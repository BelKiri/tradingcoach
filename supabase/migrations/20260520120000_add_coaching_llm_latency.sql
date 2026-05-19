-- Task 036: per-session LLM call latency (milliseconds).
ALTER TABLE public.coaching_sessions
  ADD COLUMN IF NOT EXISTS llm_latency_ms integer;

-- Down migration:
-- ALTER TABLE public.coaching_sessions DROP COLUMN IF EXISTS llm_latency_ms;
