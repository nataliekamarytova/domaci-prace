ALTER TABLE tasks ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT false;
UPDATE tasks SET is_test = true WHERE task_id IN (6, 7, 8);

-- staré placeholder úkoly (nahrazené reálným katalogem v migraci 003), bez odkazujících
-- completions, bezpečné smazat úplně
DELETE FROM tasks WHERE task_id IN (1, 2, 3, 4, 5);
