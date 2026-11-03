Domaci-prace app – tasks/users backend + frontend

Zajišťuje úkoly a uživatele a servíruje jednoduchý frontend (`../frontend`). Při splnění
úkolu volá scoring službu v `python/` (`POST /completions`), aby spočítala a uložila body.

## Jak spustit

1. Spusť obě databáze (chores i tasks): `docker compose up -d` (v rootu repa)
2. Spusť scoring službu: v `python/` `uv run fastapi dev main.py` (port 8000)
3. Spusť tento backend: `uv sync` a pak `uv run fastapi dev main.py --port 8001`
4. Otevři http://127.0.0.1:8001 (frontend) nebo http://127.0.0.1:8001/docs (API)

## Project structure

- `main.py` – API endpointy (/api/users, /api/tasks, /api/tasks/{id}/complete, /api/completions),
  servíruje statický `../frontend`
- `db.py` – databázové spojení a migrační runner (vlastní DB `tasks` na portu 5433)
- `migrations/` – SQL migrace, aplikují se automaticky při startu
