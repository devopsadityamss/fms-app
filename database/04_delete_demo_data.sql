-- 04_delete_demo_data.sql
-- Safely deletes ONLY demo seeded data

-------------------------
-- 1. Delete demo tasks
-------------------------
DELETE FROM tasks
WHERE title LIKE 'Task %'
  AND description LIKE 'Demo task number %';

-------------------------
-- 2. Delete demo projects
-------------------------
DELETE FROM projects
WHERE name IN (
  'Krishi Support System',
  'Crop Analytics Dashboard',
  'Task Automation Engine'
);

-------------------------
-- 3. Delete demo profiles
-- Only those inserted by seed file (matching Indian demo names)
-------------------------
DELETE FROM profiles
WHERE email IN (
  'ramesh.kumar@example.com',
  'priya.sharma@example.com',
  'anil.desai@example.com',
  'sunita.rao@example.com',
  'vikram.singh@example.com',
  'meena.iyer@example.com',
  'deepak.chawla@example.com'
);
