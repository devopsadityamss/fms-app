-- 02_demo_profiles_and_projects.sql

INSERT INTO profiles (id, full_name, email, role, created_at)
VALUES
  (gen_random_uuid(), 'Ramesh Kumar', 'ramesh.kumar@example.com', 'admin', now()),
  (gen_random_uuid(), 'Priya Sharma', 'priya.sharma@example.com', 'manager', now()),
  (gen_random_uuid(), 'Anil Desai', 'anil.desai@example.com', 'developer', now()),
  (gen_random_uuid(), 'Sunita Rao', 'sunita.rao@example.com', 'tester', now()),
  (gen_random_uuid(), 'Vikram Singh', 'vikram.singh@example.com', 'viewer', now()),
  (gen_random_uuid(), 'Meena Iyer', 'meena.iyer@example.com', 'developer', now()),
  (gen_random_uuid(), 'Deepak Chawla', 'deepak.chawla@example.com', 'developer', now())
ON CONFLICT(email) DO NOTHING;

INSERT INTO projects (id, name, description, created_at)
VALUES
  (gen_random_uuid(), 'Krishi Support System', 'Farmer-centric workflow automation', now()),
  (gen_random_uuid(), 'Crop Analytics Dashboard', 'Insights for crop cycles and yield', now()),
  (gen_random_uuid(), 'Task Automation Engine', 'Auto assignment of field tasks', now());
