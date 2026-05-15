
-- Accounts table: persistent trading accounts per user
CREATE TABLE accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    name text NOT NULL,
    broker text,
    starting_balance numeric,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(user_id, name)
);

-- Enable RLS
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;

-- RLS policy: users can only see their own accounts
CREATE POLICY "users_own_accounts" ON accounts
    FOR ALL USING (user_id = auth.uid());

-- Add account_id to trades (nullable for backward compat during transition)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS account_id uuid REFERENCES accounts(id);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_trades_account_id ON trades(account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
;
