-- 01_patches.sql

-- Ensure full_name exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS full_name TEXT;

-- Ensure metadata exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Ensure role exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS role TEXT;

-- Ensure avatar_url exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- Ensure email exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email TEXT UNIQUE;

-- Ensure created/updated timestamps exist
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- Ensure project columns exist
ALTER TABLE projects ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

-- Fix priority column if needed
ALTER TABLE tasks ALTER COLUMN priority SET DEFAULT 1;

-- Ensure task timestamps exist
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
