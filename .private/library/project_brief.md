# TradeCoach — AI Trading Coach for Retail Traders
## Project Brief (March 2026)

---

## What we're building

An AI-powered trading coach that helps retail FX and crypto traders fix behavioral mistakes. The product analyzes trade history, detects psychological patterns (revenge trading, overtrading, martingale, averaging down), and provides personalized AI coaching.

Core insight: traders lose money because of psychology, not strategy. No existing tool combines behavioral analysis with AI coaching on the trader's own data.

Platform: **Web dashboard (primary) + Telegram bot (secondary)**. Shared backend serves both.

---

## Product positioning

"AI trading coach that fixes your habits, not your strategy."

TradeCoach is NOT another dashboard like Myfxbook. Myfxbook shows WHAT happened. TradeCoach shows WHY it happened and coaches you to fix it.

### Competitor positioning
- **vs Myfxbook/FXBlue**: we have behavioral analysis + AI coaching (they don't)
- **vs 3Commas**: we coach you to trade better (they automate trading)
- **vs TradesViz**: we have AI coaching + simpler UX (they have more charts but no coaching)
- **vs Nansen/CoinGlass**: we analyze YOUR trades (they analyze the market)

---

## Target audience

**Primary**: Retail FX and crypto traders with 1-3 years experience, account size $2K-50K, who know the problem is discipline.

**Markets**: MENA (UAE, Saudi), Africa (Nigeria, Kenya), Southeast Asia (Indonesia, Philippines) — underserved regions with growing retail trading.

**Hybrid FX + Crypto**: same product, both markets. Crypto traders get API auto-import advantage. FX traders get CSV/Excel upload + future MT4 API.

**Secondary (later)**: FX/crypto brokers who want to reduce client churn with white-label AI coaching.

---

## Current state — what's built

### Backend services (9 modules)
- **trade_analyzer.py** — all math: win rate, P&L, profit factor, max drawdown (from peak equity), streaks, risk per trade (forex + gold pip calc), session/symbol/day/hour analysis, revenge trading, overtrading, martingale, quick exits, averaging down, weekend holds, worst hours, SL usage
- **report_generator.py** — full analysis report: overview, strengths, weaknesses, behavioral patterns, timing analysis, risk assessment
- **coaching.py** — AI coaching: builds rich context from trade data, sends to LLM for personalized insights (120-word limit, references specific dates/amounts)
- **llm.py** — LLM router: GPT-4o-mini (fast queries) + Claude Sonnet (deep analysis), cost tracking per call
- **risk_checker.py** — pre-trade validation: risk calc, daily limits, streak detection
- **emotion_tracker.py** — behavioral pattern correlation from trade data
- **habit_scorer.py** — Trading Habit Score (0-100) calculation
- **_helpers.py** — shared utilities: datetime parsing, net profit, winner/loser detection, session classification
- **contract_specs.py** — smart contract size detection from real trade data (forex, gold, indices)

### Parsers
- **mt4_parser.py** — MT4/MT5 CSV (tab and comma delimited, auto-detection)
- **xlsx_parser.py** — universal Excel parser (any broker format, auto-detects headers, fuzzy column mapping, handles dual Price/Time columns, strips symbol suffixes)

### Telegram bot
- **Account system**: create named accounts with starting balance, select, clear trades
- **File upload**: CSV/Excel upload with guided flow, cross-format deduplication
- **Full report**: per-account analysis with period filter (7/30/90 days, this week/month, custom range)
- **AI coaching**: personalized analysis powered by Claude Sonnet, cost shown per call
- **/terms**: glossary with exact detection thresholds
- **/reset**: two-step confirmation, deletes all user data
- 22 handlers, reply keyboard (3 buttons) + inline keyboards for all flows

### Database (Supabase, EU region)
- 6 tables with RLS: users, accounts, trades, emotions, user_settings, habit_scores
- `users.id` references `auth.users(id)` — Supabase Auth is identity source
- Dedup key: (symbol, opened_at rounded to minute, direction, lot)

### AI layer
- **llm.py**: GPT-4o-mini for fast queries, Claude Sonnet for deep analysis, automatic routing
- **coaching.py**: builds context from 50 recent trades with behavioral tags, session/pair breakdowns, revenge/martingale/overtrading sequences — sends to LLM for ONE surprising insight

### Tests
- **509+ tests** across 9 test files, all verified against manual calculations and real 81-trade Supabase dataset
- Covers: trade analyzer, report generator, risk checker, emotion tracker, habit scorer, MT4 parser, Excel parser, bot handlers, DB queries

### Git
- Repository: https://github.com/BelKiri/tradeguard.git

### Removed features
- Manual trade logging (/log) — CSV/Excel is primary input
- Emotion tracking buttons — behavior detected automatically from trade data
- TOP RECOMMENDATIONS section — removed from free report, moved to paid AI coaching
- Pre-trade check (/check) — code exists but hidden from bot UI

---

## Web MVP plan

### Website structure — three zones

**1. Landing page** (tradecoach.ai)
- Marketing site with 3D/animations
- Built with Framer + Spline
- Goal: registration

**2. Main/Home page** (after login)
- Account cards with quick stats across all accounts
- Last AI coaching snippet
- Upload button
- Upgrade CTA
- Beautiful but functional

**3. Dashboard** (per account)
- Full analytics: equity curve, PnL calendar heatmap
- Behavioral analysis cards (revenge, martingale, overtrading, averaging, quick exits)
- Trades table with filters
- P&L by pair/session/day charts
- Stats cards: P&L, win rate, profit factor, drawdown, expectancy
- Risk assessment, SL usage

### Web MVP features — Iteration 1 (10 days)
- Auth (Supabase Auth, Google + email login)
- Drag-and-drop file upload (CSV/Excel)
- Account creation (name, balance)
- Full dashboard with all analytics
- AI Coaching: first analysis FREE, subsequent = Pro
- Coaching history (list of past AI sessions)
- Landing page
- Mobile responsive

### Iteration 2 (after 20 users)
- API import (Binance, Bybit — auto-sync trades)
- Period comparison (this month vs last)
- Progress tracking (coaching session history, metric trends)
- Economic calendar widget
- Position size / pip value calculators (SEO lead magnets)
- Stripe payments (Free → Pro)
- Pre-trade check in web

### NOT building
- Community/leaderboards
- Custom dashboards
- Sentiment widgets
- Educational content
- Multi-account comparison (later)

---

## Tech stack

| Component | Technology | Cost | Status |
|---|---|---|---|
| Backend API | Python + FastAPI | Free | **BUILT** |
| Telegram Bot | python-telegram-bot | Free | **BUILT** |
| Database | Supabase (PostgreSQL, EU region) | Free tier | **BUILT** |
| Auth | Supabase Auth (Google + email) | Free tier | PLANNED |
| Fast LLM | GPT-4o-mini | ~$0.20/user/month | **BUILT** |
| Deep LLM | Claude Sonnet | ~$4/user/month | **BUILT** |
| Web Frontend | Next.js 14 + Tailwind + shadcn/ui | Free | PLANNED |
| Charts | Lightweight Charts (TradingView) | Free | PLANNED |
| Landing Page | Framer + Spline (3D) | Free/low | PLANNED |
| Frontend Hosting | Vercel | Free tier | PLANNED |
| Backend Hosting | Railway | ~$5-10/month | PLANNED |
| Payments | Stripe | 2.9% per tx | PLANNED |

**Total MVP cost**: $5-15/month before first paying user.
**Cost per user**: $1-2/month (LLM API calls).
**Price**: $9-19/month (test pricing after 50 free users).

---

## Architecture

```
DELIVERY LAYER (thin clients):
├── Web Dashboard (Next.js)   ──┐
├── Telegram Bot               ──┼── TradeCoach Backend API (FastAPI)
└── [Future] White-label API   ──┘

BACKEND API (FastAPI, Python):
├── /upload    — file upload endpoint (CSV/Excel)
├── /trades    — CRUD for trade data
├── /dashboard — computed stats (pure math, no AI)
├── /coaching  — AI coaching analysis
├── /webhook   — Telegram webhook receiver
└── /auth      — Supabase Auth integration

SERVICES (business logic):
├── trade_analyzer.py   — BUILT: all math and behavioral detection
├── report_generator.py — BUILT: full analysis report
├── coaching.py         — BUILT: AI coaching with trade context
├── llm.py              — BUILT: GPT-4o-mini + Claude Sonnet router
├── risk_checker.py     — BUILT: pre-trade validation
├── habit_scorer.py     — BUILT: habit score calculation
├── emotion_tracker.py  — BUILT: behavioral pattern correlation
├── _helpers.py         — BUILT: shared utilities
└── contract_specs.py   — BUILT: smart contract detection

PARSERS:
├── mt4_parser.py   — BUILT: MT4/MT5 CSV (tab + comma)
└── xlsx_parser.py  — BUILT: Universal Excel (any broker)

BOT:
├── handlers.py     — BUILT: 22 handlers, account-centric flows
└── keyboards.py    — BUILT: reply + inline keyboards

DATA:
├── Supabase (PostgreSQL) — 6 tables with RLS
└── models.py + queries.py — Pydantic models + Supabase CRUD
```

### Code structure
```
tradecoach/
├── config.py                  # settings via pydantic-settings
├── main.py                    # FastAPI app factory
├── services/
│   ├── _helpers.py            # shared: _to_dt, _net_profit, _is_winner, _session_for_hour
│   ├── trade_analyzer.py      # all math + behavioral detection
│   ├── report_generator.py    # full report builder
│   ├── coaching.py            # AI coaching context + LLM call
│   ├── llm.py                 # LLM router (GPT-4o-mini + Claude Sonnet)
│   ├── risk_checker.py        # pre-trade risk validation
│   ├── habit_scorer.py        # Trading Habit Score
│   ├── emotion_tracker.py     # behavioral correlation
│   └── contract_specs.py      # contract size detection
├── parsers/
│   ├── mt4_parser.py          # MT4/MT5 CSV parser
│   └── xlsx_parser.py         # Universal Excel parser
├── bot/
│   ├── handlers.py            # 22 handlers
│   └── keyboards.py           # reply + inline keyboards
└── db/
    ├── models.py              # Pydantic models
    └── queries.py             # Supabase CRUD

tests/                         # 509+ tests across 9 files
```

---

## Pricing strategy

### Free tier
- Upload trades (unlimited)
- Full analytics dashboard
- First AI coaching session free

### Pro ($9-19/month, test pricing after 50 free users)
- Unlimited AI coaching
- Progress tracking month over month
- API auto-sync (Binance, Bybit)
- Period comparison
- AI memory (gets smarter over time)

### Pro lock-in features
The longer a user stays, the more valuable the product becomes:

1. **Progress tracking** — AI tracks behavioral changes month over month. "Month 1: 11 revenge trades. Month 3: 3. You reduced revenge trading by 73%."
2. **AI memory** — after 3+ months, the AI knows personal patterns: which pairs trigger emotions, what time of day is worst, how you respond to losing streaks. Starting over = losing all that context.
3. **Weekly challenges + streaks** — AI gives one specific challenge per week based on actual data. "Week 12 without revenge trading." Breaking a streak hurts.
4. **Personal trading playbook** — AI builds a personalized rulebook: best pairs, best sessions, optimal lot size, patterns to avoid. Updated monthly.
5. **Period comparison** — "Q1 vs Q2: win rate +12%, drawdown -40%, revenge trades -60%." More data = more valuable comparisons.

### B2B white-label (future)
- $500-3,000/month per broker
- API + customizable prompts + admin dashboard

---

## Development timeline

### Phase 1: Backend + Telegram bot (DONE)
- FastAPI project, Supabase schema (6 tables with RLS)
- MT4/MT5 CSV parser + universal Excel parser
- trade_analyzer.py: complete behavioral analysis engine
- report_generator.py: full analysis report
- Account-centric Telegram bot with all flows
- Cross-format deduplication
- 509+ tests

### Phase 2: AI coaching (DONE)
- LLM router (GPT-4o-mini + Claude Sonnet)
- AI coaching with rich trade context (50 trades, behavioral tags, sequences)
- Personalized insights: references specific dates, amounts, patterns
- Cost tracking per LLM call

### Phase 3: Code quality + refactoring (DONE)
- Extracted shared helpers (_helpers.py), eliminated duplication across 4 files
- Standardized session hours (Asian 0-8, London 8-16, NY 16-24)
- Split oversized functions (coaching, report generator, handlers)
- Removed recommendations from free report (moved to paid AI coaching)

### Phase 4: Web MVP — Iteration 1 (NEXT, 10 days)
- Landing page (Framer + Spline)
- Supabase Auth (Google + email)
- Next.js dashboard: equity curve, PnL heatmap, behavioral cards, trades table, charts
- Drag-and-drop file upload
- AI coaching (first free, then Pro)
- Coaching history
- Mobile responsive
- Deploy: Vercel (frontend) + Railway (backend + bot)

### Phase 5: Growth — Iteration 2 (after 20 users)
- API import (Binance, Bybit auto-sync)
- Period comparison
- Progress tracking
- Stripe payments (Free → Pro)
- SEO tools (position size calc, pip value calc)
- Economic calendar widget

### Phase 6: Scale
- B2B white-label for brokers
- MT4/MT5 API direct connect
- More exchange APIs

---

## Risks and mitigations

### AI giving wrong numbers
All numbers computed programmatically in trade_analyzer.py. LLM receives pre-calculated data and only generates coaching insights. Never trusts LLM for math.

### AI giving financial advice
System prompt: "You are an analyst, not an advisor. Show facts and patterns. Never say 'buy' or 'sell'." Legal disclaimer at registration.

### Different file formats across brokers
Universal Excel parser auto-detects headers, fuzzy-matches columns, handles any broker export. CSV parser handles tab/comma delimited. Tested with real exports from multiple brokers.

### Coupling delivery layer with business logic
Telegram bot and web dashboard are THIN CLIENTS. All analytics live in services/. Adding a new client = just another API consumer.

---

## Success metrics

| Metric | Month 1 | Month 3 | Month 6 |
|---|---|---|---|
| Registered users | 100 | 500 | 2,000 |
| Daily active | 20 | 100 | 400 |
| File uploads per day | 10 | 50 | 200 |
| Free → Pro conversion | 5% | 8% | 10% |
| Paying users | 5 | 40 | 200 |
| MRR | $70 | $560 | $2,800 |
| Monthly churn | — | 15% | 10% |

---

*Last updated: March 2026*
