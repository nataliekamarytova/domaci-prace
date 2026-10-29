import psycopg
import os

DATABASE_URL = "postgresql://chores:chores@localhost:5432/chores"

def init_db(): #fce slouzici k vytvoreni scoring tabulky, dle nejnovejsi migrace
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """) #vytvori tabulku schema_migrations pokuzd uz nebude existovat s primarnim klicem filename a datumem

            cur.execute("SELECT filename FROM schema_migrations") #ptame se tabulky schema_migrations, ktere migrace uz probehly (ktere jsou zde zapsane)
            applied = [row[0] for row in cur.fetchall()] #list comprehension ntic na []

            for filename in sorted(os.listdir("migrations")): #projde všechny soubory ve složce migrations, seřazené podle jména
                if not filename.endswith(".sql") or filename in applied: #přeskočí soubor, pokud nekončí na .sql (třeba omylem uložený jiný soubor) nebo už je v seznamu proběhlých.
                    continue

                with open(os.path.join("migrations", filename)) as f: #otevře soubor a přečti jeho obsah do proměnné sql
                    sql = f.read()

                cur.execute(sql) #spustí obsah souboru v DB
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                ) #zapiše do tabulky schema_migrations, že tenhle soubor proběhl. Příště se přeskočí.
                print(f"Applied migration: {filename}") #do terminálu vypíše, která migrace právě proběhla, ať víme