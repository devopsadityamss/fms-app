UPDATE auth.users
SET email_confirmed_at = NOW()
WHERE email = 'test@fms.com';



ALTER TABLE projects
ADD COLUMN updated_at TIMESTAMPTZ;





UPDATE projects SET updated_at = NOW() WHERE updated_at IS NULL;

-- Optional: set default timestamp on update
ALTER TABLE projects
ALTER COLUMN updated_at SET DEFAULT NOW();




SELECT * FROM projects ORDER BY created_at DESC;
