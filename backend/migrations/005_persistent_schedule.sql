-- Pro sdílené pravidelné úkoly (daily/weekly/monthly, ne TEST s pevným deadline, ne myčku)
-- potřebujeme "živý" termín, který se neresetuje automaticky s kalendářem, ale zůstává
-- otevřený (a po hard_deadline zaseknutý na 25 %), dokud ho někdo nesplní. Nová instance
-- se spustí až od začátku následujícího období.
ALTER TABLE tasks ADD COLUMN current_deadline TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN current_hard_deadline TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN current_completed_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN current_points_awarded INT;
ALTER TABLE tasks ADD COLUMN current_completed_by INT REFERENCES users(user_id);
