-- 05_validate_demo_state.sql

WITH demo_profiles AS (
    SELECT COUNT(*) AS c
    FROM profiles
    WHERE email IN (
      'ramesh.kumar@example.com',
      'priya.sharma@example.com',
      'anil.desai@example.com',
      'sunita.rao@example.com',
      'vikram.singh@example.com',
      'meena.iyer@example.com',
      'deepak.chawla@example.com'
    )
),

demo_projects AS (
    SELECT COUNT(*) AS c
    FROM projects
    WHERE name IN (
      'Krishi Support System',
      'Crop Analytics Dashboard',
      'Task Automation Engine'
    )
),

demo_tasks AS (
    SELECT COUNT(*) AS c
    FROM tasks
    WHERE title LIKE 'Task %'
      AND description LIKE 'Demo task number %'
)

SELECT 
  (SELECT c FROM demo_profiles)  AS demo_profiles_count,
  (SELECT c FROM demo_projects)  AS demo_projects_count,
  (SELECT c FROM demo_tasks)     AS demo_tasks_count,
  CASE 
    WHEN (SELECT c FROM demo_profiles) = 0
     AND (SELECT c FROM demo_projects) = 0
     AND (SELECT c FROM demo_tasks) = 0
    THEN 'DEMO DATA REMOVED'
    
    WHEN (SELECT c FROM demo_profiles) > 0
     AND (SELECT c FROM demo_projects) > 0
     AND (SELECT c FROM demo_tasks) > 0
    THEN 'DEMO DATA PRESENT'
    
    ELSE 'PARTIAL / INCONSISTENT — NEEDS CHECK'
  END AS state;
