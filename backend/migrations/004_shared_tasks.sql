-- shared = true: splnění kýmkoliv počítá pro všechny (žádný další to už nemůže udělat
--                znovu v témže období) - výchozí chování pro většinu domácích úkolů
-- shared = false: každé splnění se počítá zvlášť, libovolně opakovaně (např. myčka,
--                 kterou můžeme pustit i vícekrát denně)
ALTER TABLE tasks ADD COLUMN shared BOOLEAN NOT NULL DEFAULT true;

UPDATE tasks SET shared = false WHERE name = 'Naskládat/zapnout/vyklidit myčku';
