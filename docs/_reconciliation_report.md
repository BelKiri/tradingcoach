## Brief vs Code Reconciliation — Task 001 Phase 2

### Confirmed (brief matches code)

- **Backend framework**: brief says Python + FastAPI; code uses FastAPI with routers under `/api/*`. Evidence: `tradecoach/main.py:46-73`
- **Telegram bot framework**: brief says `python-telegram-bot`; bot imports `telegram` / `telegram.ext` (not aiogram). Evidence: `tradecoach/bot/handlers.py:28-35`, `requirements.txt:7`
- **LLM quick path**: brief says GPT-4o-mini for fast queries; `quick_query` uses `gpt-4o-mini`. Evidence: `tradecoach/services/llm.py:92-109`
- **LLM deep path**: brief says Claude Sonnet for deep analysis; `deep_analysis` routes coaching/analysis/review to Anthropic. Evidence: `tradecoach/services/llm.py:158-175`, `tradecoach/services/llm.py:230-233`
- **LLM routing**: brief describes automatic quick vs deep routing; `route_query` maps query types to `QueryType`. Evidence: `tradecoach/services/llm.py:221-233`
- **Coaching context size**: brief says 50 recent trades; coaching sorts and takes the last 50. Evidence: `tradecoach/services/coaching.py:296-309`, `tradecoach/services/coaching.py:789`
- **Coaching length limit**: brief says 120-word limit; legacy coaching prompt caps at 120 words. Evidence: `tradecoach/services/coaching.py:739`
- **Core service modules**: brief lists `trade_analyzer.py`, `report_generator.py`, `coaching.py`, `llm.py`, `risk_checker.py`, `emotion_tracker.py`, `habit_scorer.py`, `_helpers.py`; all are present under `tradecoach/services/`. Evidence: `tradecoach/services/`
- **Parsers**: brief lists `mt4_parser.py` and `xlsx_parser.py`; both exist under `tradecoach/parsers/`. Evidence: `tradecoach/parsers/`
- **Supabase data model (core 6 tables)**: brief lists `users`, `accounts`, `trades`, `emotions`, `user_settings`, `habit_scores`; Pydantic models and CRUD queries use the same names. Evidence: `tradecoach/db/models.py:20-173`, `tradecoach/db/queries.py:64-401`
- **Trade dedup key**: brief says `(symbol, opened_at rounded to minute, direction, lot)`; queries expose the same tuple. Evidence: `tradecoach/db/queries.py:221-248`
- **Bot reply keyboard**: brief says 3 reply buttons; keyboards define Upload, My Accounts, Premium. Evidence: `tradecoach/bot/keyboards.py:21-24`
- **Market data provider keys**: brief does not detail TwelveData/Finnhub, but code configures both API keys. Evidence: `tradecoach/config.py:37-39`, `tradecoach/services/market_data.py:58-139`, `tradecoach/services/news.py:74-110`
- **Tests exceed brief minimum**: brief says 509+ tests across 9 files; `pytest --collect-only` reports 653 tests in 16 files under `tests/`. Evidence: `tests/`, `pytest --collect-only`
- **Git remote is `tradingcoach`**: brief still links `tradeguard.git`; `origin` is `https://github.com/BelKiri/tradingcoach.git`. Evidence: `git remote -v`

### Changed (code differs from brief)

- **Deep LLM model ID**: brief says “Claude Sonnet”; code pins `claude-sonnet-4-20250514` (dated Sonnet 4 snapshot). Evidence: `tradecoach/services/llm.py:49`, `tradecoach/services/llm.py:175`
- **Telegram handler count**: brief says 22 handlers; `setup_handlers` registers 23 top-level `app.add_handler` calls (6 commands, 3 `ConversationHandler`s, 14 other handlers). Evidence: `tradecoach/bot/handlers.py:1156-1254`
- **Backend service count**: brief lists 9 backend modules; `tradecoach/services/` has 12 Python files (adds `market_data.py`, `calendar.py`, `news.py`, `news_collector.py`; omits `contract_specs.py` from the brief list). Evidence: `tradecoach/services/`, `docs/project_brief.md:44-53`
- **Web frontend status**: brief marks Next.js 14 + Tailwind + shadcn as PLANNED and Phase 4 Web MVP as NEXT; repo has a `frontend/` Next.js 14 app with marketing, auth, dashboard, coaching, checker, and tools routes. Evidence: `docs/project_brief.md:155-156`, `docs/project_brief.md:290-298`, `frontend/package.json:21`, `frontend/app/`
- **Auth status**: brief marks Supabase Auth as PLANNED; frontend has OAuth callback route and Supabase SSR deps; backend exposes JWT verification via `tradecoach/api/auth.py` (dependency, not a mounted router). Evidence: `docs/project_brief.md:152`, `frontend/app/auth/callback/route.ts:1-18`, `frontend/package.json:16-17`, `tradecoach/api/auth.py:1-39`
- **Charts library**: brief plans Lightweight Charts (TradingView); dashboard charts use Recharts. Evidence: `docs/project_brief.md:156`, `frontend/package.json:24`, `frontend/components/dashboard/equity-curve-chart.tsx:4`
- **API route map**: brief lists `/upload`, `/trades`, `/dashboard`, `/coaching`, `/webhook`, `/auth`; FastAPI mounts `/api/upload`, `/api/trades`, `/api/dashboard`, `/api/analysis`, `/api/coaching`, `/api/accounts`, `/api/users`, plus `/health` — no `/webhook` or `/auth` router in `main.py`. Evidence: `docs/project_brief.md:177-182`, `tradecoach/main.py:67-78`
- **CORS / Vercel naming**: production allowlist includes `https://tradeguard-cyan.vercel.app`, not `tradingcoach`. Evidence: `tradecoach/main.py:56-60`
- **Test file count**: brief says 9 test files; `tests/` contains 16 `test_*.py` modules. Evidence: `docs/project_brief.md:78-80`, `tests/`
- **Iteration 2 web scope**: brief defers economic calendar, calculators, and Stripe to Iteration 2; marketing routes already include economic calendar and calculator pages. Evidence: `docs/project_brief.md:127-134`, `frontend/app/(marketing)/tools/`
- **News collection schedule**: `requirements.txt` comments mention APScheduler for briefings/RAG; runtime uses a FastAPI `asyncio` loop every 30 minutes instead. Evidence: `requirements.txt:39-40`, `tradecoach/main.py:17-40`

### Unclear (need Mr.K input)

- **Backend hosting**: brief still plans Railway; Task 001 context says production moved to Hetzner CPX22 Falkenstein — no hosting provider appears in application code or env templates reviewed here. Evidence: `docs/project_brief.md:159`, `docs/project_brief.md:298`, `docs/tasks/001-docs-bootstrap.md:15`
- **Claude Haiku 4.5**: Task 001 context mentions Haiku 4.5 alongside Sonnet 4.6; repository has no `claude-haiku` / `haiku` model strings in Python or frontend code. Evidence: repo-wide search (only task file mentions Haiku)
- **“Claude Sonnet 4.6” vs `claude-sonnet-4-20250514`**: code uses an Anthropic snapshot ID; whether that is the intended Sonnet 4.6 production choice is not documented in code. Evidence: `tradecoach/services/llm.py:175`
- **Supabase project metadata**: brief documents project name `tradecoach` and ID `hxessnrcskxjqdjpegkn` (Frankfurt); code reads `supabase_url` / keys from env only — cannot confirm project ID or region from code alone. Evidence: `docs/project_brief.md:68-69`, `tradecoach/config.py:23-26`
- **Stripe**: `stripe` is in `requirements.txt` and settings expose Stripe secrets, but no `import stripe` usage was found in Python sources — unclear if payments are wired or only scaffolded. Evidence: `requirements.txt:42-43`, `tradecoach/config.py:41-43`
- **RAG / ChromaDB**: `chromadb` is listed in `requirements.txt` with a RAG comment, but no Python imports of ChromaDB were found — unclear if planned, removed, or not yet integrated. Evidence: `requirements.txt:16-17`
- **Web MVP completion vs brief timeline**: substantial `frontend/` and `v0/` trees exist while the March 2026 brief still labels Web MVP as the next 10-day phase — unclear which surfaces are production vs prototype. Evidence: `docs/project_brief.md:290-298`, `frontend/`, `v0/`
- **Handler count semantics**: brief’s “22 handlers” may count conversation sub-handlers differently from top-level `app.add_handler` registrations (23 today). Evidence: `tradecoach/bot/handlers.py:1156-1254`

### Missing from brief (in code but undocumented)

- **`contract_specs.py` absent**: brief lists smart contract size detection module; no `contract_specs.py` under `tradecoach/services/` or elsewhere in the repo. Evidence: `docs/project_brief.md:53`, repo search
- **`market_data.py`**: TwelveData OHLC/ATR/volatility pipeline with on-disk price cache. Evidence: `tradecoach/services/market_data.py:1-50`, `tradecoach/services/market_data.py:135-139`
- **`calendar.py`**: static economic calendar JSON, timezone conversion, event matching. Evidence: `tradecoach/services/calendar.py:1-16`, `tradecoach/services/calendar.py:22-36`
- **`news.py` / `news_collector.py`**: Finnhub headline fetch, instrument matching, Supabase persistence on a 30-minute background loop. Evidence: `tradecoach/services/news.py:86-110`, `tradecoach/services/news_collector.py:1-40`, `tradecoach/main.py:20-40`
- **`news` table**: collector reads/writes `news` beyond the brief’s six core tables. Evidence: `tradecoach/services/news_collector.py:37-80`
- **`coaching_sessions` table**: coaching API and service persist session history. Evidence: `tradecoach/services/coaching.py:610-656`, `tradecoach/api/coaching.py:146-177`
- **`/api/analysis` router**: analysis endpoints mounted in FastAPI; not in the brief architecture diagram. Evidence: `tradecoach/main.py:70`
- **`/api/accounts` and `/api/users` routers**: account and user APIs beyond the brief’s minimal route list. Evidence: `tradecoach/main.py:72-73`
- **JWT auth dependency module**: `tradecoach/api/auth.py` verifies Supabase bearer tokens for protected routes. Evidence: `tradecoach/api/auth.py:1-39`
- **Bot `/premium` command and Premium reply button**: registered in handlers/keyboards; not enumerated in the brief’s bot feature list. Evidence: `tradecoach/bot/handlers.py:1164-1165`, `tradecoach/bot/keyboards.py:24`, `tradecoach/bot/keyboards.py:1164`
- **Declared but unused Python deps**: `chromadb`, `apscheduler`, and `stripe` appear in `requirements.txt` without matching imports in `.py` sources searched. Evidence: `requirements.txt:16-17`, `requirements.txt:39-43`, repo-wide import search
- **Additional Python stack deps**: `pandas-ta`, `feedparser`, `beautifulsoup4`, `aiohttp` are installed but not reflected in the brief tech table. Evidence: `requirements.txt:27-37`
- **No SQL migrations in repo**: schema evolution is not versioned in-tree (Supabase may hold migrations externally). Evidence: no `migrations/` directory in repo
- **`v0/` Next.js prototype**: separate app tree (newer Next lockfile references Next 16 in `v0/`) not mentioned in the brief. Evidence: `v0/`
- **Root-level `test_real_*.py` scripts**: live integration scripts outside `tests/` not counted in the brief’s test inventory. Evidence: repository root `test_real_*.py`
