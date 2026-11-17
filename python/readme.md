Domaci-prace app – scoring service

Calculates and stores points for completed household tasks, based on the task's
priority and how close to its deadline it was completed.

## How to run

1. Start the database: `docker compose up -d`
2. Install dependencies: `uv sync`
3. Run the app: `uv run fastapi dev main.py`
4. Open API docs: http://127.0.0.1:8000/docs

## Project structure

- `main.py` – API endpoints
- `db.py` – database connection and migration runner
- `migrations/` – SQL migrations, applied automatically on startup

## Adding a migration

Create a new file in `migrations/` with the next number,
e.g. `002_add_foreign_keys.sql`. Never edit migrations
that have already been applied.
