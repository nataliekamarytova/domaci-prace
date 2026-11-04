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
    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT t.task_id, t.name, t.base_points, t.priority,
                          (t.deadline IS NOT NULL AND t.deadline < now()) AS overdue,
                          c.points_awarded
                   FROM tasks t
                   LEFT JOIN completions c
                     ON c.task_id = t.task_id
                    AND c.user_id = %s
                    AND c.completed_date = now()::date
                   ORDER BY t.task_id""",
                (user_id,),
            )
            rows = cur.fetchall()
    return [
        {
            "task_id": r[0],
            "name": r[1],
            "base_points": r[2],
            "priority": r[3],
            "overdue": r[4] and r[5] is None,
            "done_today": r[5] is not None,
            "points_awarded": r[5],
        }
        for r in rows
    ]


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, body: CompleteTaskRequest):
    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT name, base_points, priority, deadline FROM tasks WHERE task_id = %s",
                (task_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Task not found")
            task_name, base_points, priority, fixed_deadline = row

            completed_at = datetime.now().astimezone()
            deadline = fixed_deadline or datetime.combine(
                completed_at.date(), time(23, 59, 59), tzinfo=completed_at.tzinfo
            )
            hard_deadline = deadline + HARD_DEADLINE_OFFSET

            cur.execute(
                """SELECT 1 FROM completions
                   WHERE task_id = %s AND user_id = %s AND completed_date = %s""",
                (task_id, body.user_id, completed_at.date()),
            )
            if cur.fetchone() is not None:
                raise HTTPException(status_code=400, detail="Task already completed today")

            cur.execute(
                """INSERT INTO completions (task_id, user_id, completed_at, completed_date)
                   VALUES (%s, %s, %s, %s) RETURNING completion_id""",
                (task_id, body.user_id, completed_at, completed_at.date()),
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
            "task_deadline": deadline.isoformat(),
            "task_hard_deadline": hard_deadline.isoformat(),
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


@app.get("/health")
async def get_health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
