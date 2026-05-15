
-- Add broker_source to trades table
ALTER TABLE trades ADD COLUMN IF NOT EXISTS broker_source text;

-- Add account_balance and broker_name to user_settings
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS account_balance numeric;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS broker_name text;
;
