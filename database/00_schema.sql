-- 00_schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-------------------------
-- profiles
-------------------------
CREATE TABLE profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  avatar_url TEXT,
  email TEXT UNIQUE,
  full_name TEXT,
  role TEXT
);

-------------------------
-- projects
-------------------------
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-------------------------
-- tasks status enum
-------------------------
CREATE TYPE task_status AS ENUM ('pending','in_progress','completed');

-------------------------
-- tasks
-------------------------
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status task_status DEFAULT 'pending',
  priority INT DEFAULT 1,
  assignee_id UUID REFERENCES profiles(id),
  reporter_id UUID REFERENCES profiles(id),
  due_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
