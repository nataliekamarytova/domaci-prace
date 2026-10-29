from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
from db import DATABASE_URL,init_db
import psycopg

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()    # spustí se při startu aplikace
    yield        # tady aplikace běží

app = FastAPI(lifespan=lifespan)

class Completion(BaseModel):
    id:int
    user_id: int
    task_id: int
    task_name: str
    task_priority: int
    task_deadline: datetime | None = None
    task_completed_at: datetime

@app.post("/completions")
def get_completion(completion:Completion):
    with psycopg.connect(DATABASE_URL) as con:
        with con.cursor() as cur:
            cur.execute("INSERT INTO scoring(user_id,task_id,received_points) VALUES (%s,%s,%s)",(completion.user_id,completion.task_id,0))
    #uložit hodnoty do db
    result = {"points": 0,**completion.model_dump()}
    return(result)
    
  
@app.get("/health")
async def get_health():
    return {"status":"ok"}


# @app.get("/db-test")
# def db_test():
#     with psycopg.connect(DATABASE_URL) as conn:
#         with conn.cursor() as cur:
#             cur.execute("SELECT version()")
#             return {"postgres": cur.fetchone()[0]}
    

# @app.put("/items/{item_id}")
# async def update_item(item_id: int, item: Item, q: str | None = None):
#     result = {"item_id": item_id, **item.model_dump()}
#     if q:
#         result.update({"q": q})
#     return result