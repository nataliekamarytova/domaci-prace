import calendar
import os
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import init_db, pool

SCORING_SERVICE_URL = os.environ.get("SCORING_SERVICE_URL", "http://localhost:8000")

# Hard deadline pro úkoly s pevným deadline (testovací "TEST:" úkoly) = deadline + 3 dny.
HARD_DEADLINE_OFFSET = timedelta(days=3)


def compute_schedule(frequency, fixed_deadline, now):
    """Vrátí (deadline, hard_deadline, period_key) pro daný úkol k danému okamžiku.

    period_key jednoznačně identifikuje "aktuální období" (den/týden/měsíc), ve kterém
    se úkol počítá jako splněný - používá se pro dedup (jen jedno splnění za období).
    Pro fixní (testovací) a nepravidelné úkoly se dedup podle období neřeší.
    """
    if fixed_deadline is not None:
        deadline = fixed_deadline
        hard_deadline = deadline + HARD_DEADLINE_OFFSET
        return deadline, hard_deadline, "fixed"

    today = now.date()

    if frequency == "daily":
        deadline = datetime.combine(today, time(17, 0, 0), tzinfo=now.tzinfo)
        hard_deadline = datetime.combine(today + timedelta(days=1), time(9, 0, 0), tzinfo=now.tzinfo)
        period_key = today.isoformat()

    elif frequency == "weekly":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        deadline = datetime.combine(sunday, time(23, 59, 59), tzinfo=now.tzinfo)
        hard_deadline = datetime.combine(sunday + timedelta(days=1), time(23, 59, 59), tzinfo=now.tzinfo)
        period_key = f"week:{monday.isoformat()}"

    elif frequency == "monthly":
        last_day = calendar.monthrange(today.year, today.month)[1]
        month_end = today.replace(day=last_day)
        deadline = datetime.combine(month_end, time(23, 59, 59), tzinfo=now.tzinfo)
        hard_deadline = deadline + timedelta(days=7)
        period_key = today.strftime("%Y-%m")

    elif frequency == "irregular":
        return None, None, None

    else:
        raise ValueError(f"unknown frequency: {frequency}")

    return deadline, hard_deadline, period_key


def uses_persistent_schedule(fixed_deadline, frequency, shared):
    """Sdílené pravidelné úkoly (ne TEST s pevným deadline, ne nesdílené typu myčka,
    ne nepravidelné) mají "živý" termín - neresetuje se sám s kalendářem, ale zůstává
    otevřený (po hard_deadline zaseknutý na 25 %), dokud ho někdo nesplní."""
    return fixed_deadline is None and shared and frequency != "irregular"


def compute_persistent_schedule(frequency, instance_start):
    """Deadline/hard_deadline pro novou instanci "živého" úkolu, počítané jako plovoucí
    okno od chvíle, kdy se úkol zpřístupnil (ne ukotvené na konkrétní den v kalendáři -
    jinak by se u týdenních/měsíčních úkolů okno na splnění mohlo zkrátit v závislosti na
    tom, kdy přesně nová instance nastartovala)."""
    if frequency == "daily":
        deadline = datetime.combine(instance_start.date(), time(17, 0, 0), tzinfo=instance_start.tzinfo)
        hard_deadline = datetime.combine(
            instance_start.date() + timedelta(days=1), time(9, 0, 0), tzinfo=instance_start.tzinfo
        )
    elif frequency == "weekly":
        deadline_date = instance_start.date() + timedelta(days=7)
        deadline = datetime.combine(deadline_date, time(23, 59, 59), tzinfo=instance_start.tzinfo)
        hard_deadline = datetime.combine(
            deadline_date + timedelta(days=1), time(23, 59, 59), tzinfo=instance_start.tzinfo
        )
    elif frequency == "monthly":
        last_day = calendar.monthrange(instance_start.year, instance_start.month)[1]
        month_end = instance_start.date().replace(day=last_day)
        deadline = datetime.combine(month_end, time(23, 59, 59), tzinfo=instance_start.tzinfo)
        hard_deadline = deadline + timedelta(days=7)
    else:
        raise ValueError(f"unexpected frequency: {frequency}")
    return deadline, hard_deadline


def get_or_advance_schedule(cur, task_id, frequency, current_deadline, current_hard_deadline,
                             current_completed_at, current_points_awarded, current_completed_by, now):
    """Vrátí (deadline, hard_deadline, done, points_awarded, completed_by) pro úkol
    s "živým" termínem a případně v DB posune na novou instanci, pokud už začalo
    další období po tom, co byla ta předchozí splněná."""
    if current_deadline is None:
        deadline, hard_deadline = compute_persistent_schedule(frequency, now)
        cur.execute(
            """UPDATE tasks SET current_deadline = %s, current_hard_deadline = %s,
                                 current_completed_at = NULL, current_points_awarded = NULL,
                                 current_completed_by = NULL
               WHERE task_id = %s""",
            (deadline, hard_deadline, task_id),
        )
        return deadline, hard_deadline, False, None, None

    if current_completed_at is not None:
        next_period_start = datetime.combine(
            current_deadline.date() + timedelta(days=1), time(0, 0), tzinfo=current_deadline.tzinfo
        )
        if now >= next_period_start:
            deadline, hard_deadline = compute_persistent_schedule(frequency, next_period_start)
            cur.execute(
                """UPDATE tasks SET current_deadline = %s, current_hard_deadline = %s,
                                     current_completed_at = NULL, current_points_awarded = NULL,
                                     current_completed_by = NULL
                   WHERE task_id = %s""",
                (deadline, hard_deadline, task_id),
            )
            return deadline, hard_deadline, False, None, None
        return current_deadline, current_hard_deadline, True, current_points_awarded, current_completed_by

    return current_deadline, current_hard_deadline, False, None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    init_db()
    yield
    pool.close()


app = FastAPI(lifespan=lifespan)


class CompleteTaskRequest(BaseModel):
    user_id: int


@app.get("/api/users")
def list_users():
    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT user_id, name FROM users ORDER BY user_id")
            rows = cur.fetchall()
    return [{"user_id": r[0], "name": r[1]} for r in rows]


@app.get("/api/checklist/{user_id}")
def get_checklist(user_id: int):
    now = datetime.now().astimezone()

    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT task_id, name, base_points, priority, deadline, frequency, shared,
                          current_deadline, current_hard_deadline, current_completed_at,
                          current_points_awarded, current_completed_by
                   FROM tasks WHERE active = true ORDER BY task_id"""
            )
            tasks = cur.fetchall()

            # sdílené úkoly bez živého termínu (myčka, nepravidelné): splnění kýmkoliv
            # se počítá pro všechny, proto se nefiltruje na konkrétního uživatele
            cur.execute(
                """SELECT c.task_id, c.period_key, c.points_awarded, u.name
                   FROM completions c JOIN users u ON u.user_id = c.user_id"""
            )
            completions_by_key = {}
            for task_id, period_key, points_awarded, user_name in cur.fetchall():
                completions_by_key.setdefault((task_id, period_key), (points_awarded, user_name))

            # nesdílené úkoly (myčka) - kolikrát a kým byly dnes splněny, i když
            # zůstávají dál zaškrtnutelné (viz "shared" ve frontendu)
            cur.execute(
                """SELECT c.task_id, u.name, COUNT(*) AS cnt
                   FROM completions c JOIN users u ON u.user_id = c.user_id
                   WHERE c.completed_date = %s
                   GROUP BY c.task_id, u.name""",
                (now.date(),),
            )
            completed_today = {}
            for task_id, user_name, cnt in cur.fetchall():
                completed_today.setdefault(task_id, []).append({"name": user_name, "count": cnt})

            result = []
            for (task_id, name, base_points, priority, fixed_deadline, frequency, shared,
                 current_deadline, current_hard_deadline, current_completed_at,
                 current_points_awarded, current_completed_by) in tasks:

                if uses_persistent_schedule(fixed_deadline, frequency, shared):
                    deadline, _hd, done, points_awarded, completed_by_id = get_or_advance_schedule(
                        cur, task_id, frequency, current_deadline, current_hard_deadline,
                        current_completed_at, current_points_awarded, current_completed_by, now,
                    )
                    completed_by = None
                    if completed_by_id is not None:
                        cur.execute("SELECT name FROM users WHERE user_id = %s", (completed_by_id,))
                        completed_by = cur.fetchone()[0]
                else:
                    deadline, _hd, period_key = compute_schedule(frequency, fixed_deadline, now)
                    done = False
                    points_awarded = None
                    completed_by = None
                    if shared and period_key is not None:
                        match = completions_by_key.get((task_id, period_key))
                        if match is not None:
                            points_awarded, completed_by = match
                            done = True

                overdue = deadline is not None and deadline < now and not done
                result.append(
                    {
                        "task_id": task_id,
                        "name": name,
                        "base_points": base_points,
                        "priority": priority,
                        "frequency": frequency,
                        "shared": shared,
                        "done": done,
                        "overdue": overdue,
                        "points_awarded": points_awarded,
                        "completed_by": completed_by,
                        "completed_today": completed_today.get(task_id, []),
                    }
                )
    return result


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, body: CompleteTaskRequest):
    completed_at = datetime.now().astimezone()

    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT name, base_points, priority, deadline, frequency, shared,
                          current_deadline, current_hard_deadline, current_completed_at,
                          current_points_awarded, current_completed_by
                   FROM tasks WHERE task_id = %s AND active = true""",
                (task_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Task not found")
            (task_name, base_points, priority, fixed_deadline, frequency, shared,
             current_deadline, current_hard_deadline, current_completed_at,
             current_points_awarded, current_completed_by) = row

            persistent = uses_persistent_schedule(fixed_deadline, frequency, shared)

            if persistent:
                deadline, hard_deadline, done, _pts, _by = get_or_advance_schedule(
                    cur, task_id, frequency, current_deadline, current_hard_deadline,
                    current_completed_at, current_points_awarded, current_completed_by, completed_at,
                )
                if done:
                    raise HTTPException(status_code=400, detail="Task already completed for this period")
                period_key = None  # dedup u perzistentních úkolů řeší current_completed_at, ne period_key
            else:
                deadline, hard_deadline, period_key = compute_schedule(frequency, fixed_deadline, completed_at)

                if period_key is not None and shared:
                    # sdílený úkol bez živého termínu - jakmile ho splní kdokoliv,
                    # nikdo další ho v tomtéž období už splnit nemůže
                    cur.execute(
                        "SELECT 1 FROM completions WHERE task_id = %s AND period_key = %s",
                        (task_id, period_key),
                    )
                    if cur.fetchone() is not None:
                        raise HTTPException(status_code=400, detail="Task already completed for this period")

                if not shared:
                    # nesdílený úkol (myčka) - libovolně opakovatelné, i tímtéž uživatelem
                    # ve stejném období, proto se neukládá period_key (víc NULL hodnot
                    # UNIQUE (task_id, user_id, period_key) nepovažuje za duplicitu)
                    period_key = None

            cur.execute(
                """INSERT INTO completions (task_id, user_id, completed_at, completed_date, period_key)
                   VALUES (%s, %s, %s, %s, %s) RETURNING completion_id""",
                (task_id, body.user_id, completed_at, completed_at.date(), period_key),
            )
            completion_id = cur.fetchone()[0]

    response = httpx.post(
        f"{SCORING_SERVICE_URL}/completions",
        json={
            "id": completion_id,
            "user_id": body.user_id,
            "task_id": task_id,
            "task_name": task_name,
            "task_priority": priority,
            "task_deadline": deadline.isoformat() if deadline else None,
            "task_hard_deadline": hard_deadline.isoformat() if hard_deadline else None,
            "task_completed_at": completed_at.isoformat(),
            "base_points": base_points,
        },
    )
    response.raise_for_status()
    points = response.json()["points"]

    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE completions SET points_awarded = %s WHERE completion_id = %s",
                (points, completion_id),
            )
            if persistent:
                cur.execute(
                    """UPDATE tasks SET current_completed_at = %s, current_points_awarded = %s,
                                         current_completed_by = %s
                       WHERE task_id = %s""",
                    (completed_at, points, body.user_id, task_id),
                )

    return {"task_id": task_id, "points_awarded": points}


@app.get("/api/completions")
def list_completions():
    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT c.completion_id, t.name, u.name, c.completed_at, c.points_awarded
                   FROM completions c
                   JOIN tasks t ON t.task_id = c.task_id
                   JOIN users u ON u.user_id = c.user_id
                   ORDER BY c.completed_at DESC
                   LIMIT 50"""
            )
            rows = cur.fetchall()
    return [
        {
            "completion_id": r[0],
            "task_name": r[1],
            "user_name": r[2],
            "completed_at": r[3],
            "points_awarded": r[4],
        }
        for r in rows
    ]


@app.get("/health")
async def get_health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
