
-- 1. Drop FK constraint tying public.users.id to auth.users
ALTER TABLE public.users DROP CONSTRAINT users_id_fkey;

-- 2. Add default UUID generation so bot can insert without specifying id
ALTER TABLE public.users ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- 3. Drop all existing auth.uid()-based RLS policies

-- users
DROP POLICY IF EXISTS users_select_own ON public.users;
DROP POLICY IF EXISTS users_update_own ON public.users;

-- trades
DROP POLICY IF EXISTS trades_select_own ON public.trades;
DROP POLICY IF EXISTS trades_insert_own ON public.trades;
DROP POLICY IF EXISTS trades_update_own ON public.trades;
DROP POLICY IF EXISTS trades_delete_own ON public.trades;

-- emotions
DROP POLICY IF EXISTS emotions_select_own ON public.emotions;
DROP POLICY IF EXISTS emotions_insert_own ON public.emotions;
DROP POLICY IF EXISTS emotions_update_own ON public.emotions;
DROP POLICY IF EXISTS emotions_delete_own ON public.emotions;

-- user_settings
DROP POLICY IF EXISTS settings_select_own ON public.user_settings;
DROP POLICY IF EXISTS settings_insert_own ON public.user_settings;
DROP POLICY IF EXISTS settings_update_own ON public.user_settings;

-- habit_scores
DROP POLICY IF EXISTS scores_select_own ON public.habit_scores;
DROP POLICY IF EXISTS scores_insert_own ON public.habit_scores;

-- 4. Create new RLS policies
--    service_role bypasses RLS automatically, so these policies
--    only matter for the anon/authenticated roles (future web frontend).
--    For now, allow authenticated users to access their own rows.

-- users: authenticated users can read/update their own row
CREATE POLICY users_select_own ON public.users
  FOR SELECT TO authenticated USING (id = auth.uid());
CREATE POLICY users_update_own ON public.users
  FOR UPDATE TO authenticated USING (id = auth.uid());

-- trades: authenticated users CRUD their own rows
CREATE POLICY trades_select_own ON public.trades
  FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY trades_insert_own ON public.trades
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY trades_update_own ON public.trades
  FOR UPDATE TO authenticated USING (user_id = auth.uid());
CREATE POLICY trades_delete_own ON public.trades
  FOR DELETE TO authenticated USING (user_id = auth.uid());

-- emotions
CREATE POLICY emotions_select_own ON public.emotions
  FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY emotions_insert_own ON public.emotions
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY emotions_update_own ON public.emotions
  FOR UPDATE TO authenticated USING (user_id = auth.uid());
CREATE POLICY emotions_delete_own ON public.emotions
  FOR DELETE TO authenticated USING (user_id = auth.uid());

-- user_settings
CREATE POLICY settings_select_own ON public.user_settings
  FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY settings_insert_own ON public.user_settings
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY settings_update_own ON public.user_settings
  FOR UPDATE TO authenticated USING (user_id = auth.uid());

-- habit_scores
CREATE POLICY scores_select_own ON public.habit_scores
  FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY scores_insert_own ON public.habit_scores
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
;
