import psycopg
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

DATABASE_URL = "postgresql://chores:chores@localhost:5432/chores"

app = FastAPI()

class Completion(BaseModel):
    user_id: int
    task_id: int
    task_priority: int
    task_deadline: datetime | None = None
    task_completed_at: datetime

@app.post("/completions")
async def get_completion(completion:Completion):
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