-- TEST úkoly sloužily jen k ladění scoringu, do finální appky nepatří
UPDATE tasks SET active = false WHERE is_test = true;
