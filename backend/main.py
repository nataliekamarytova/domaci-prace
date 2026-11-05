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

# Placeholder - čeká se na přesné pravidlo od přítele, zatím deadline + 3 dny.
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
        hard_deadline = deadline + timedelta(days=7)  # placeholder, čeká na upřesnění
        period_key = today.strftime("%Y-%m")

    elif frequency == "irregular":
        return None, None, None

    else:
        raise ValueError(f"unknown frequency: {frequency}")

    return deadline, hard_deadline, period_key


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
                """SELECT task_id, name, base_points, priority, deadline, frequency
                   FROM tasks WHERE active = true ORDER BY task_id"""
            )
            tasks = cur.fetchall()

            cur.execute(
                "SELECT task_id, period_key, points_awarded FROM completions WHERE user_id = %s",
                (user_id,),
            )
            points_by_key = {(r[0], r[1]): r[2] for r in cur.fetchall()}

    result = []
    for task_id, name, base_points, priority, fixed_deadline, frequency in tasks:
        deadline, _hard_deadline, period_key = compute_schedule(frequency, fixed_deadline, now)
        points_awarded = points_by_key.get((task_id, period_key)) if period_key is not None else None
        done = points_awarded is not None
        overdue = deadline is not None and deadline < now and not done
        result.append(
            {
                "task_id": task_id,
                "name": name,
                "base_points": base_points,
                "priority": priority,
                "frequency": frequency,
                "done": done,
                "overdue": overdue,
                "points_awarded": points_awarded,
            }
        )
    return result


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, body: CompleteTaskRequest):
    completed_at = datetime.now().astimezone()

    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT name, base_points, priority, deadline, frequency
                   FROM tasks WHERE task_id = %s AND active = true""",
                (task_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Task not found")
            task_name, base_points, priority, fixed_deadline, frequency = row

            deadline, hard_deadline, period_key = compute_schedule(frequency, fixed_deadline, completed_at)

            if period_key is not None:
                cur.execute(
                    """SELECT 1 FROM completions
                       WHERE task_id = %s AND user_id = %s AND period_key = %s""",
                    (task_id, body.user_id, period_key),
                )
                if cur.fetchone() is not None:
                    raise HTTPException(status_code=400, detail="Task already completed for this period")

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
