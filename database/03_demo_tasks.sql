-- 03_demo_tasks.sql

WITH prof AS (
  SELECT id, full_name FROM profiles ORDER BY created_at LIMIT 5
),
proj AS (
  SELECT id FROM projects ORDER BY created_at LIMIT 3
)
INSERT INTO tasks (project_id, title, description, status, priority, assignee_id, reporter_id, due_date)
SELECT
  (SELECT id FROM proj ORDER BY random() LIMIT 1),
  CONCAT('Task ', g),
  CONCAT('Demo task number ', g),
  (CASE WHEN random() < 0.33 THEN 'pending'
        WHEN random() < 0.66 THEN 'in_progress'
        ELSE 'completed' END)::task_status,
  1 + (random() * 3)::int,
  (SELECT id FROM prof ORDER BY random() LIMIT 1),
  (SELECT id FROM prof ORDER BY random() LIMIT 1),
  now() + (g || ' days')::interval
FROM generate_series(1, 20) g;
