-- Structured session feedback on coaching_sessions.
ALTER TABLE public.coaching_sessions
  ADD COLUMN IF NOT EXISTS feedback_rating integer,
  ADD COLUMN IF NOT EXISTS feedback_comment text,
  ADD COLUMN IF NOT EXISTS feedback_learned_new boolean,
  ADD COLUMN IF NOT EXISTS feedback_submitted_at timestamp with time zone;

-- Down migration:
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS feedback_submitted_at;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS feedback_learned_new;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS feedback_comment;
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS feedback_rating;
