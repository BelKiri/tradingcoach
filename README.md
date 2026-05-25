# TradingCoach

AI trading Coach for retail traders. Behavioral pattern detection grounded in your real trade history.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-MVP-orange.svg)
![Powered by](https://img.shields.io/badge/powered_by-Claude_Sonnet_4.6-5436DA.svg)

🔗 **Try it:** [trading-coach.app](https://trading-coach.app)

📊 **Status:** MVP shipped May 2026 · First cohort of 10 traders active

🛠 **Stack:** Python 3.12 · FastAPI · Next.js 14 · Supabase · Claude Sonnet 4.6

<p align="center">
  <img
    src="https://github.com/user-attachments/assets/70849178-7a72-4e5c-be3a-5d71952ec68e"
    alt="TradingCoach AI Coach output — prioritized action plan for reducing losses, generated from the trader's real trade history"
    width="900"
  />
</p>
<p align="center">
  <em>AI Coach output: a prioritized action plan grounded in the trader's real history.</em>
</p>

---

## The problem

Active retail traders frequently lose money due to psychological factors rather than flawed strategies. In interviews, many traders expressed confusion, stating, "I don't understand why I'm losing money." Most trading journals do not address this issue; they typically record outcomes like win rate, P&L, and basic statistics, but rarely track behavioral patterns or connect trades to these factors. As a result, traders often review their results without understanding the underlying causes of their losses.

## The solution

TradingCoach analyzes your trading history to identify behavioral patterns, including revenge trading, martingale, overtrading, quick exits, weekend holds, and correlations with macroeconomic events and trading indicators. The AI coach then delivers clear insights, highlighting specific dates, symbols, and amounts from your data. You receive a structured report outlining your strengths, weaknesses, and actionable recommendations to help reduce losses.

## Demo

**Dashboard — analytics and behavioral patterns at a glance**

<p align="center">
  <img
    src="https://github.com/user-attachments/assets/00e74e67-62c1-4e99-8650-54d03d80dd1d"
    alt="TradingCoach dashboard showing P&L metrics, equity curve, behavioral pattern cards, and trade timing breakdowns for a connected trading account"
    width="900"
  />
</p>

**AI Coach — full analysis with behavioral insights**

<p align="center">
  <img
    src="https://github.com/user-attachments/assets/a72c7f27-f4d4-46df-814a-633ac257e8fb"
    alt="Full AI Coach analysis output showing behavioral pattern findings, account performance summary, and specific actionable recommendations grounded in the trader's actual trade history"
    width="900"
  />
</p>

## How it works

1. Upload a trade journal exported from MetaTrader 4/5 (CSV) or Excel
   from any broker.
2. Select the time zone in which transactions are shown.
3. The backend parses and stores trades, normalized to UTC.
4. A Python pipeline runs deterministic classification: P&L breakdowns,
   behavioral patterns, session and timing analysis, volatility flagging.
5. The coaching engine assembles a structured context (full account
   history + behavioral tags + economic calendar matches + per-symbol
   ATR-based volatility) and sends it to Claude Sonnet for a single
   generation pass.
6. The trader receives a personalized coaching insight, rendered through
   a safe markdown parser.

## Architecture

The frontend (Next.js, hosted on Vercel) calls a FastAPI backend (deployed via Docker Compose on a self-managed EU VPS) through a server-side proxy.

Supabase handles authentication (Google OAuth) and Postgres storage. All trade math and behavioral classification runs in Python on structured data — the LLM is never used for classification.

Claude is invoked once per coaching session to convert a pre-computed context into a human-readable insight.

Architectural rationale for the choices below lives in [docs/decisions/](docs/decisions/).

## AI approach

The product intentionally separates AI tasks. Behavioral pattern detection, session analysis, news matching, and volatility flagging are handled by deterministic Python processes that are fast, testable, and reproducible. Claude Sonnet 4.6 is used exclusively to convert structured context into a personalized coaching narrative for the trader.

This context includes complete account trade history, behavioral pattern tags, session and timing breakdowns, trades flagged near significant macro events from a curated economic calendar, and per-symbol volatility analysis using ATR calculated over the 14 days before each trade.

Before launching the first cohort, coaching outputs were manually validated against real trade histories for factual accuracy. Consistency was checked across multiple runs on identical inputs, with responses being approximately 95% identical and only minor, non-critical wording differences. LLM output is processed through a secure markdown parser to protect the UI from unsafe HTML.

## How TradingCoach compares

Most trading analyzers report outcomes such as win rate, P&L, and equity curve. TradingCoach goes further by explaining the reasons behind results in clear, actionable language and recommending steps to address issues. It also compares each trade with external data, including a curated economic calendar and ATR-based volatility, to provide context that most trade journals do not capture.

## Key decisions

- [LLM stack — single-model Claude Sonnet 4.6](docs/decisions/002-llm-stack-sonnet-only.md)
  — one vendor, one model, no router; all classification stays in Python
  where it can be tested deterministically.
- [UTC timestamp convention](docs/decisions/005-utc-timestamp-convention.md)
  — store UTC, convert with `broker_timezone` only at the import edge and
  at user-perspective aggregation edges; external joins (sessions, macro
  events, market data) use UTC directly.
- [Self-managed VPS over PaaS](docs/decisions/003-backend-hosting-vps.md)
  — predictable flat cost, EU data residency, room to colocate future
  services without re-architecting.
- [AI Coach quota during MVP beta](docs/decisions/007-ai-coach-quota-beta.md)
  — bounded LLM spend with explicit per-account and lifetime caps,
  enforced server-side before any LLM call.

## Tech stack

- **Backend:** Python 3.12, FastAPI, Docker Compose
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Database & auth:** Supabase (Postgres + Auth with Google OAuth, EU region)
- **AI:** Anthropic Claude Sonnet 4.6
- **Market data:** TwelveData (OHLC, ATR)
- **Hosting:** Self-managed EU VPS (backend), Vercel (frontend)

## Status

MVP shipped May 2026. First cohort of 10 traders active. Public
registration is not yet open.

See [ROADMAP.md](ROADMAP.md) for what's next.

## Getting started

Requirements: Python 3.12, Node.js 20+, Docker.

```bash
git clone https://github.com/BelKiri/tradingcoach
cd tradingcoach
cp .env.example .env  # fill in API keys
docker compose up -d --build
cd frontend && npm install && npm run dev
```

Visit `http://localhost:3000`.

Health check: `curl http://localhost:8000/health`.

Configuration variables live in `.env.example`. Tests run with `pytest tests/unit/`.

## License

[MIT](LICENSE)

## About this project

TradingCoach is built as a portfolio piece for the transition into a
Senior AI Product Manager role, combining three years of fintech product
management with hands-on AI engineering. Architectural decisions are
recorded in [docs/decisions/](docs/decisions/), features are documented
in [docs/features/](docs/features/), and changes are tracked in
[CHANGELOG.md](CHANGELOG.md).

Contact: [LinkedIn](https://www.linkedin.com/in/kirill-beliaev/)
