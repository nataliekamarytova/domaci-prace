"""Vygeneruje synteticka data za poslednich ~6 tydnu, castecne podle realneho rozdeleni
prace v domacnosti. Pouziva skutecnou scoring sluzbu (python/main.py na portu 8000),
takze body jsou spocitane realnym get_points, ne vymyslene natvrdo.

U sdilenych pravidelnych ukolu (daily/weekly/monthly, ne mycka, ne nepravidelne) simuluje
"zivy" retezec instanci presne jako realna aplikace: instance zustava otevrena (po
hard_deadline zaseknuta na 25 %), dokud ji nekdo nesplni, a dalsi instance zacne az
den po jejim deadline.

Spusteni: uv run python seed_synthetic_data.py  (z backend/, scoring sluzba musi bezet)
"""
import random
from datetime import datetime, timedelta, time, date

import httpx

from db import pool
from main import compute_schedule, compute_persistent_schedule, uses_persistent_schedule

random.seed(42)

SCORING_SERVICE_URL = "http://localhost:8000"
USER_NATALIE = 1
USER_JAKUB = 2

WEEKS_OF_HISTORY = 6
TODAY = date.today()
START_DATE = TODAY - timedelta(weeks=WEEKS_OF_HISTORY)
END_DATE = TODAY - timedelta(days=1)  # dnešek necháváme čistý pro reálné používání
START_MOMENT = datetime.combine(START_DATE, time(8, 0)).astimezone()
END_MOMENT = datetime.combine(END_DATE, time(23, 59, 59)).astimezone()

# pravděpodobnost, že úkol udělá Jakub (zbytek připadá Natálii) - u sdílených úkolů
JAKUB_SHARE = {
    "Vynést kočičí záchod": 0.95,
    "Vysát": 0.25,
    "Vynést odpad": 0.5,
}
DEFAULT_JAKUB_SHARE = 0.2

# myčka je shared=false - oba nezávisle, vlastní denní pravděpodobnost
DISHWASHER_DAILY_PROB = {USER_NATALIE: 0.75, USER_JAKUB: 0.12}

IRREGULAR_WEEKLY_PROB = 0.5

TIMING = {
    USER_NATALIE: {"on_time": 0.85, "late": 0.12, "very_late": 0.03},
    USER_JAKUB: {"on_time": 0.55, "late": 0.30, "very_late": 0.15},
}


def pick_user_for_shared_task(task_name):
    jakub_prob = JAKUB_SHARE.get(task_name, DEFAULT_JAKUB_SHARE)
    return USER_JAKUB if random.random() < jakub_prob else USER_NATALIE


def pick_timing_bucket(user_id):
    r = random.random()
    probs = TIMING[user_id]
    if r < probs["on_time"]:
        return "on_time"
    if r < probs["on_time"] + probs["late"]:
        return "late"
    return "very_late"


def random_moment_between(start, end):
    if end <= start:
        return start
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.uniform(0, delta))


def sample_completed_at(bucket, period_start, deadline, hard_deadline):
    if bucket == "on_time":
        return random_moment_between(period_start, deadline)
    if bucket == "late":
        return random_moment_between(deadline, hard_deadline)
    return hard_deadline + timedelta(hours=random.uniform(1, 96))


def call_scoring(client, completion_id, task_id, task_name, base_points, priority,
                  user_id, deadline, hard_deadline, completed_at):
    response = client.post(
        f"{SCORING_SERVICE_URL}/completions",
        json={
            "id": completion_id,
            "user_id": user_id,
            "task_id": task_id,
            "task_name": task_name,
            "task_priority": priority,
            "task_deadline": deadline.isoformat() if deadline else None,
            "task_hard_deadline": hard_deadline.isoformat() if hard_deadline else None,
            "task_completed_at": completed_at.isoformat(),
            "base_points": base_points,
            "note": "synthetic",
        },
    )
    response.raise_for_status()
    return response.json()["points"]


def insert_completion(cur, task_id, user_id, completed_at, period_key):
    cur.execute(
        """INSERT INTO completions (task_id, user_id, completed_at, completed_date, period_key)
           VALUES (%s, %s, %s, %s, %s) RETURNING completion_id""",
        (task_id, user_id, completed_at, completed_at.date(), period_key),
    )
    return cur.fetchone()[0]


def simulate_persistent_task(cur, client, task_id, name, base_points, priority, frequency):
    """Simuluje "živý" řetězec instancí pro sdílený pravidelný úkol - stejně, jak by to
    dělala reálná aplikace při každodenním používání posledních ~6 týdnů."""
    created = 0
    instance_start = START_MOMENT

    while True:
        deadline, hard_deadline = compute_persistent_schedule(frequency, instance_start)
        user_id = pick_user_for_shared_task(name)
        bucket = pick_timing_bucket(user_id)
        completed_at = sample_completed_at(bucket, instance_start, deadline, hard_deadline)

        if completed_at > END_MOMENT:
            # tahle instance zůstává nesplněná - aplikace ji ukáže jako aktuálně
            # otevřenou/opožděnou, přesně jako u reálného používání
            cur.execute(
                """UPDATE tasks SET current_deadline = %s, current_hard_deadline = %s,
                                     current_completed_at = NULL, current_points_awarded = NULL,
                                     current_completed_by = NULL
                   WHERE task_id = %s""",
                (deadline, hard_deadline, task_id),
            )
            return created

        completion_id = insert_completion(cur, task_id, user_id, completed_at, None)
        points = call_scoring(
            client, completion_id, task_id, name, base_points, priority,
            user_id, deadline, hard_deadline, completed_at,
        )
        cur.execute(
            "UPDATE completions SET points_awarded = %s WHERE completion_id = %s",
            (points, completion_id),
        )
        cur.execute(
            """UPDATE tasks SET current_deadline = %s, current_hard_deadline = %s,
                                 current_completed_at = %s, current_points_awarded = %s,
                                 current_completed_by = %s
               WHERE task_id = %s""",
            (deadline, hard_deadline, completed_at, points, user_id, task_id),
        )
        created += 1

        next_period_start = datetime.combine(
            deadline.date() + timedelta(days=1), time(0, 0), tzinfo=deadline.tzinfo
        )
        if next_period_start > END_MOMENT:
            return created
        instance_start = next_period_start


def simulate_dishwasher(cur, client, task_id, name, base_points, priority, frequency):
    created = 0
    current = START_DATE
    while current <= END_DATE:
        ref = datetime.combine(current, time(12, 0)).astimezone()
        deadline, hard_deadline, _period_key = compute_schedule(frequency, None, ref)
        for user_id, prob in DISHWASHER_DAILY_PROB.items():
            if random.random() < prob:
                bucket = pick_timing_bucket(user_id)
                period_start = datetime.combine(current, time(7, 0)).astimezone()
                completed_at = sample_completed_at(bucket, period_start, deadline, hard_deadline)
                completion_id = insert_completion(cur, task_id, user_id, completed_at, current.isoformat())
                points = call_scoring(
                    client, completion_id, task_id, name, base_points, priority,
                    user_id, deadline, hard_deadline, completed_at,
                )
                cur.execute(
                    "UPDATE completions SET points_awarded = %s WHERE completion_id = %s",
                    (points, completion_id),
                )
                created += 1
        current += timedelta(days=1)
    return created


def simulate_irregular(cur, client, task_id, name, base_points, priority):
    created = 0
    current = START_DATE
    while current <= END_DATE:
        if random.random() < IRREGULAR_WEEKLY_PROB:
            user_id = pick_user_for_shared_task(name)
            day_offset = random.randint(0, 6)
            event_date = min(current + timedelta(days=day_offset), END_DATE)
            completed_at = datetime.combine(
                event_date, time(random.randint(7, 21), random.randint(0, 59))
            ).astimezone()
            completion_id = insert_completion(cur, task_id, user_id, completed_at, None)
            points = call_scoring(
                client, completion_id, task_id, name, base_points, priority,
                user_id, None, None, completed_at,
            )
            cur.execute(
                "UPDATE completions SET points_awarded = %s WHERE completion_id = %s",
                (points, completion_id),
            )
            created += 1
        current += timedelta(days=7)
    return created


def main():
    total_created = 0
    with httpx.Client() as client:
        with pool.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    """SELECT task_id, name, base_points, priority, frequency, shared, deadline
                       FROM tasks WHERE active = true AND name NOT LIKE 'TEST:%%'
                       ORDER BY task_id"""
                )
                tasks = cur.fetchall()

                for task_id, name, base_points, priority, frequency, shared, fixed_deadline in tasks:
                    if frequency == "irregular":
                        total_created += simulate_irregular(cur, client, task_id, name, base_points, priority)
                    elif not shared:
                        total_created += simulate_dishwasher(
                            cur, client, task_id, name, base_points, priority, frequency
                        )
                    elif uses_persistent_schedule(fixed_deadline, frequency, shared):
                        total_created += simulate_persistent_task(
                            cur, client, task_id, name, base_points, priority, frequency
                        )

    print(f"Hotovo, vytvořeno {total_created} syntetických completions ({START_DATE} - {END_DATE}).")


if __name__ == "__main__":
    pool.open()
    main()
    pool.close()
