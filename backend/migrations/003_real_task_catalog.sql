ALTER TABLE tasks ADD COLUMN frequency TEXT NOT NULL DEFAULT 'daily'
    CHECK (frequency IN ('daily', 'weekly', 'monthly', 'irregular'));
ALTER TABLE tasks ADD COLUMN active BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE completions ADD COLUMN period_key TEXT;
ALTER TABLE completions DROP CONSTRAINT completions_task_id_user_id_completed_date_key;
ALTER TABLE completions ADD CONSTRAINT completions_task_user_period_key_key UNIQUE (task_id, user_id, period_key);

-- staré placeholder úkoly nemažeme (zachovat historii completions), jen je deaktivujeme
UPDATE tasks SET active = false WHERE task_id IN (1, 2, 3, 4, 5);

INSERT INTO tasks (name, base_points, priority, frequency) VALUES
    ('Naskládat/zapnout/vyklidit myčku', 15, 2, 'daily'),
    ('Vysát', 20, 2, 'daily'),
    ('Umýt kuchyň', 15, 2, 'daily'),
    ('Otřít prach', 10, 2, 'weekly'),
    ('Uklidit koupelnu', 25, 2, 'weekly'),
    ('Vysát gauč a škrabadla', 25, 2, 'weekly'),
    ('Vynést kočičí záchod', 15, 2, 'weekly'),
    ('Vyměnit povlečení', 15, 2, 'monthly'),
    ('Vymýt misky kočkám', 5, 2, 'irregular'),
    ('Umýt kočičí záchod', 20, 2, 'irregular'),
    ('Vynést odpad', 10, 2, 'irregular'),
    ('Zalít rostliny', 5, 2, 'irregular'),
    ('Vyprat a pověsit prádlo', 15, 2, 'irregular'),
    ('Sklidit usušené prádlo', 15, 2, 'irregular');
