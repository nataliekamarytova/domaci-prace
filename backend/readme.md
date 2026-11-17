Domaci-prace app – tasks/users backend + frontend

Manages tasks and users, and serves the simple frontend (`../frontend`). When a task is
completed, it calls the scoring service in `python/` (`POST /completions`) to calculate
and store the points.

## How to run

1. Start both databases (chores and tasks): `docker compose up -d` (from the repo root)
2. Start the scoring service: in `python/`, `uv run fastapi dev main.py` (port 8000)
3. Start this backend: `uv sync` and then `uv run fastapi dev main.py --port 8001`
4. Open http://127.0.0.1:8001 (frontend) or http://127.0.0.1:8001/docs (API)

## Project structure

- `main.py` – API endpoints (/api/users, /api/tasks, /api/tasks/{id}/complete, /api/completions),
  serves the static `../frontend`
- `db.py` – database connection and migration runner (own `tasks` database on port 5433)
- `migrations/` – SQL migrations, applied automatically on startup
