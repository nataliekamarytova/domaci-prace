import psycopg
import os
from psycopg_pool import ConnectionPool

DATABASE_URL = "postgresql://chores:chores@localhost:5432/chores"
pool = ConnectionPool(DATABASE_URL, open=False) 

def init_db(): #fce slouzici k vytvoreni scoring tabulky, dle nejnovejsi migrace
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)

            cur.execute("SELECT filename FROM schema_migrations") 
            applied = [row[0] for row in cur.fetchall()] 

            for filename in sorted(os.listdir("migrations")):
                if not filename.endswith(".sql") or filename in applied: 
                    continue

                with open(os.path.join("migrations", filename)) as f: 
                    sql = f.read()

                cur.execute(sql) 
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                ) 
                print(f"Applied migration: {filename}") 