CREATE TABLE IF NOT EXISTS users(
    user_id INT PRIMARY KEY,
    name TEXT
);

INSERT INTO users(user_id,name) VALUES (1,'Natálie');
INSERT INTO users(user_id,name) VALUES (2,'Jakub');

CREATE TABLE IF NOT EXISTS tasks(
    task_id INT PRIMARY KEY,
    name TEXT,
    frequency TEXT,
    base_points INT
);

INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (9,'Naskládat/zapnout/vyklidit myčku','daily',15);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (10,'Vysát','daily',20);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (11,'Umýt kuchyň','daily',15);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (12,'Otřít prach','weekly',10);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (13,'Uklidit koupelnu','weekly',25);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (14,'Vysát gauč a škrabadla','weekly',25);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (15,'Vynést kočičí záchod','weekly',15);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (16,'Vyměnit povlečení','monthly',15);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (17,'Vymýt misky kočkám','irregular',5);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (18,'Umýt kočičí záchod','irregular',20);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (19,'Vynést odpad','irregular',10);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (20,'Zalít rostliny','irregular',5);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (21,'Vyprat a pověsit prádlo','irregular',15);
INSERT INTO tasks(task_id,name,frequency,base_points) VALUES (22,'Sklidit usušené prádlo','irregular',15);
