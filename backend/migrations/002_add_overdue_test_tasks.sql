ALTER TABLE tasks ADD COLUMN deadline TIMESTAMPTZ;

INSERT INTO tasks (name, base_points, priority, deadline) VALUES
    ('TEST: opožděný úklid (3 dny)', 20, 2, now() - interval '3 days'),
    ('TEST: opožděný naléhavý úkol (1 den)', 20, 1, now() - interval '1 day'),
    ('TEST: hodně opožděný úkol (10 dní)', 20, 2, now() - interval '10 days');
