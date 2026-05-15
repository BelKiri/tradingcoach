ALTER TABLE accounts ADD COLUMN IF NOT EXISTS broker_timezone text DEFAULT 'UTC+2';;
