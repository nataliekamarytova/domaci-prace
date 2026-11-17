from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
from db import init_db, pool
from scoring import get_points

@asynccontextmanager
async def lifespan(app: FastAPI): 
    pool.open()  
    init_db()    
    yield       
    pool.close() 

app = FastAPI(lifespan=lifespan)

class Completion(BaseModel):
    id:int
    user_id: int
    task_id: int
    task_name: str
    task_priority: int
    task_deadline: datetime | None = None
    task_hard_deadline: datetime | None = None
    task_completed_at: datetime
    base_points: int
    note: str | None = None


@app.post("/completions")
def get_completion(completion:Completion):
    points = get_points(completion.base_points,completion.task_deadline,completion.task_completed_at,completion.task_priority,completion.task_hard_deadline)
    with pool.connection() as con:
        with con.cursor() as cur:
            cur.execute("INSERT INTO scoring(user_id,task_id,received_points,completed_at,note) VALUES (%s,%s,%s,%s,%s)",(completion.user_id,completion.task_id,points,completion.task_completed_at,completion.note))
    #uložit hodnoty do db
    result = {"points":points, **completion.model_dump()}
    return(result)
  
@app.get("/health")
async def get_health():
    return {"status":"ok"}