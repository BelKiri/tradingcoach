# Changelog

All notable changes to TradingCoach.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Persistent banner showing remaining AI Coach sessions across the app.

### Planned
- Cleanup of legacy LLM integration code
- Auth flow idempotency improvement

### Fixed
- Uploading a CSV or XLSX that contains trades already in the account no longer creates duplicates. The import now correctly recognizes overlapping history and inserts only the new trades.
- `broker_timezone` sent when creating an account is now stored on the account record.
- Google login is now functional. The "Login with Google" option on the sign-in page completes authentication and returns the user signed in.
- CSV files exported directly from the trading terminal now import correctly with timestamps preserved. Previously, CSVs with the raw broker-export column layout could result in trades that appeared in instrument totals but did not aggregate by day, hour, or trading session.

### Changed
- Landing page: removed pricing section and crypto trading FAQ; updated AI coaching FAQ wording to match current product capability.
- Frontend is now served on the canonical domain trading-coach.app; the legacy URL remains available during the transition.
- Trading account creation is now limited to 3 accounts per user during the beta. Reach out at TG: @BMNCap for expanded access.
- File uploads are limited to one per trading account during the beta. To upload a different file, delete the account and create a new one.
- AI Coach is limited to one analysis per trading account during the beta, with a total of 3 across all accounts.
- Settings page text now accurately reflects the active beta limits.
- Trade timestamps are now stored in UTC. Hour-of-day, weekday, overtrading, and equity-by-day analytics group trades using the account's broker timezone. Trading sessions (Asian, London, New York) use IANA timezone definitions with automatic daylight-saving handling. Implements ADR-005.
- Rebuilt economic calendar with USD high-impact events for 2025-2026 (added PPI, Retail Sales, ISM Services PMI)
- Fixed DST handling: event times now reflect actual UTC per date
- Asymmetric matching window: 30 min before event, 60 min after
- AI Coach analysis now renders standard markdown: headings, bold, italic, lists, horizontal rules, tables, blockquotes, inline and fenced code. Dollar amounts retain their color coding (negative red, positive green).

### Security
- AI Coach output is now rendered through a safe markdown parser. Hardens the rendering layer against unsafe HTML in model output.
- Backend API is now served over HTTPS for all production traffic from the frontend proxy.

### Documentation
- ADR-006: Canonical domain migration — apex form and CORS transition strategy.
- ADR-007: AI Coach quota policy during MVP beta.

## [0.1.0] — 2026-05-12

### Added
- Backend API (FastAPI) deployed to production
- Frontend (Next.js) connected to production backend
- AI coaching insights powered by Claude Sonnet 4.6
- Trade upload (MT4 CSV, Excel) and behavioral analysis
- Economic calendar matching
- News collection (background loop)
- User authentication via Supabase Auth + Google OAuth
- Dashboard with equity curve, win rate, profit factor

### Architecture
- Backend hosted on self-managed VPS, deployed via Docker Compose
- nginx reverse proxy for backend
- Frontend hosted on Vercel
- Supabase (Postgres + Auth) as data backend
