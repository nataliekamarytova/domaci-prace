-- TEST úkoly sloužily jen k ladění scoringu, do finální aplikace nepatří
UPDATE tasks SET active = false WHERE is_test = true;
