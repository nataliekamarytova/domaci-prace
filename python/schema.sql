CREATE TABLE IF NOT EXISTS scoring(
    score_id SERIAL PRIMARY KEY, 
    user_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    received_points INTEGER NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);