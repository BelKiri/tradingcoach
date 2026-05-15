
-- ============================================
-- TradeCoach MVP Schema
-- ============================================

-- 1. USERS
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  telegram_id bigint unique,
  username text,
  email text,
  tier text not null default 'free' check (tier in ('free', 'pro')),
  timezone text not null default 'UTC',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. TRADES
create table public.trades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  source text not null default 'csv' check (source in ('csv', 'telegram', 'api')),
  ticket bigint,
  symbol text not null,
  direction text not null check (direction in ('buy', 'sell')),
  lot numeric(10,2) not null,
  open_price numeric(12,5),
  close_price numeric(12,5),
  stop_loss numeric(12,5),
  take_profit numeric(12,5),
  profit_pips numeric(10,1),
  profit_money numeric(12,2),
  commission numeric(10,2) default 0,
  swap numeric(10,2) default 0,
  opened_at timestamptz,
  closed_at timestamptz,
  followed_plan boolean,
  moved_stop boolean,
  notes text,
  created_at timestamptz not null default now()
);

create index idx_trades_user_id on public.trades(user_id);
create index idx_trades_closed_at on public.trades(user_id, closed_at);
create index idx_trades_symbol on public.trades(user_id, symbol);

-- 3. EMOTIONS
create table public.emotions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  trade_id uuid references public.trades(id) on delete set null,
  emotion text not null check (emotion in ('calm', 'confident', 'fear', 'boredom', 'revenge')),
  context text check (context in ('pre_trade', 'post_trade', 'check_in')),
  logged_at timestamptz not null default now()
);

create index idx_emotions_user_id on public.emotions(user_id);
create index idx_emotions_trade_id on public.emotions(trade_id);

-- 4. USER_SETTINGS
create table public.user_settings (
  user_id uuid primary key references public.users(id) on delete cascade,
  max_risk_pct numeric(5,2) default 2.0,
  max_trades_per_day int default 5,
  watchlist text[] default '{}',
  preferred_sessions text[] default '{}',
  briefing_time time default '07:00',
  strategy_name text,
  strategy_rules text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 5. HABIT_SCORES
create table public.habit_scores (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  score int not null check (score between 0 and 100),
  plan_adherence numeric(5,2),
  emotional_stability numeric(5,2),
  risk_discipline numeric(5,2),
  consistency numeric(5,2),
  journal_completion numeric(5,2),
  period_start date not null,
  period_end date not null,
  created_at timestamptz not null default now()
);

create index idx_habit_scores_user_id on public.habit_scores(user_id, period_end);

-- ============================================
-- Enable RLS on all tables
-- ============================================

alter table public.users enable row level security;
alter table public.trades enable row level security;
alter table public.emotions enable row level security;
alter table public.user_settings enable row level security;
alter table public.habit_scores enable row level security;

-- ============================================
-- RLS Policies: each user sees only their own data
-- ============================================

-- users: can read/update own row
create policy "users_select_own" on public.users
  for select using (auth.uid() = id);

create policy "users_update_own" on public.users
  for update using (auth.uid() = id);

-- trades: full CRUD on own trades
create policy "trades_select_own" on public.trades
  for select using (auth.uid() = user_id);

create policy "trades_insert_own" on public.trades
  for insert with check (auth.uid() = user_id);

create policy "trades_update_own" on public.trades
  for update using (auth.uid() = user_id);

create policy "trades_delete_own" on public.trades
  for delete using (auth.uid() = user_id);

-- emotions: full CRUD on own emotions
create policy "emotions_select_own" on public.emotions
  for select using (auth.uid() = user_id);

create policy "emotions_insert_own" on public.emotions
  for insert with check (auth.uid() = user_id);

create policy "emotions_update_own" on public.emotions
  for update using (auth.uid() = user_id);

create policy "emotions_delete_own" on public.emotions
  for delete using (auth.uid() = user_id);

-- user_settings: read/insert/update own settings
create policy "settings_select_own" on public.user_settings
  for select using (auth.uid() = user_id);

create policy "settings_insert_own" on public.user_settings
  for insert with check (auth.uid() = user_id);

create policy "settings_update_own" on public.user_settings
  for update using (auth.uid() = user_id);

-- habit_scores: read own, insert own
create policy "scores_select_own" on public.habit_scores
  for select using (auth.uid() = user_id);

create policy "scores_insert_own" on public.habit_scores
  for insert with check (auth.uid() = user_id);

-- ============================================
-- updated_at trigger
-- ============================================

create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger set_updated_at before update on public.users
  for each row execute function public.handle_updated_at();

create trigger set_updated_at before update on public.user_settings
  for each row execute function public.handle_updated_at();
;
