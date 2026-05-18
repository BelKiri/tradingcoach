-- Task 034: structured action-plan rules + per-session token/cost persistence.
ALTER TABLE public.coaching_sessions
  ADD COLUMN IF NOT EXISTS rules jsonb,
  ADD COLUMN IF NOT EXISTS input_tokens integer,
  ADD COLUMN IF NOT EXISTS output_tokens integer,
  ADD COLUMN IF NOT EXISTS cost_usd numeric(10, 4);

-- Down migration:
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS rules;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS input_tokens;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS output_tokens;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS cost_usd;
