-- Beta quota enforcement: exempt flag and lifetime coaching session counter.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_beta_exempt boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS coaching_sessions_used integer NOT NULL DEFAULT 0;
