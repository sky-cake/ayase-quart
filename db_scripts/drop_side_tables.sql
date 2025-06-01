SELECT 'DROP TABLE IF EXISTS "' || name || '";'
FROM sqlite_master
WHERE type = 'table'
  AND (name LIKE '%_images' OR name LIKE '%_threads');

-- run the resulting DROP statements
-- then run VACUUM; if you want