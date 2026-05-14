**# Economic Calendar** Behavioral context for trading psychology coaching — see how news drives your decisions. 

**## The problem** Active retail traders make many of their worst decisions around high-impact economic releases — entering positions minutes before NFP, holding through FOMC volatility, revenge-trading after a CPI miss. Most trading journals show what was traded; few show whether the trade fought macro context. Without that context, behavioral coaching is half-blind. 

**## The solution** A pre-loaded calendar of high-impact US economic events (plus EU and UK central bank rate decisions) covers 2024-2026. The AI coaching pipeline matches every uploaded trade against events within an asymmetric window (30 min before event start, 60 min after) in the trader's broker timezone. The coaching insight surfaces patterns the trader didn't consciously track — like "you opened 4 of your 5 worst losers within an hour of CPI release." 

**## Status** Static calendar shipping with first user cohort. Live API integration deferred until Iteration 2 (after first paying users). 

**## Tech stack** 

- Backend: Python (FastAPI), `tradecoach/services/calendar.py` 
- Data: Static JSON at `tradecoach/data/economic_calendar.json` 
- AI integration: Calendar section in Claude Sonnet coaching prompt 
- Sources: Official release schedules from US Federal Reserve, BLS, BEA, ISM, ECB, Bank of England

**## Architecture** Trade upload triggers behavioral analysis. Coaching pipeline loads calendar events for the relevant date range, converts each trade timestamp from broker timezone to UTC, matches against event UTC times with asymmetric window. Matched events feed into AI coaching context as "trades near news" statistics. Frontend never queries calendar directly — events surface only through AI coaching output. 

**## Key decisions** 

- Static JSON over live API for MVP — see `.private/backlog/decisions-pending.md` D-002 for the live-API revisit triggers 
- USD-only scope (plus EUR/GBP rate decisions) — covers ~90% of FX/CFD retail trader exposure 
- DST-aware event times — release times stored as the actual UTC for that specific date, not season-naive UTC

**## Getting started** For local development: clone the repo, copy `.env.example` to `.env`, fill in API keys, run via Docker Compose. Calendar loads automatically when coaching is requested. 

**## About this project** 

Architecture decisions are recorded in `docs/decisions/`, feature PRDs in `docs/prd/`.

**## License** MIT
