CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    base_points INT NOT NULL,
    priority INT NOT NULL DEFAULT 2
);

CREATE TABLE completions (
    completion_id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(task_id),
    user_id INT NOT NULL REFERENCES users(user_id),
    completed_at TIMESTAMPTZ NOT NULL,
    completed_date DATE NOT NULL,
    points_awarded INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, user_id, completed_date)
);

INSERT INTO users (name) VALUES ('Natálie'), ('Jakub');

INSERT INTO tasks (name, base_points, priority) VALUES
    ('Umýt nádobí', 15, 2),
    ('Vynést koš', 10, 2),
    ('Vyluxovat', 20, 2),
    ('Uklidit kuchyň', 15, 2),
    ('Posbírat prádlo', 10, 2);
