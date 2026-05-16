# Changelog

All notable changes to TradingCoach.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Cleanup of legacy LLM integration code
- Auth flow idempotency improvement
- HTTPS for backend endpoint

### Fixed
- `broker_timezone` sent when creating an account is now stored on the account record.
- Google login is now functional. The "Login with Google" option on the sign-in page completes authentication and returns the user signed in.
- CSV files exported directly from the trading terminal now import correctly with timestamps preserved. Previously, CSVs with the raw broker-export column layout could result in trades that appeared in instrument totals but did not aggregate by day, hour, or trading session.

### Changed
- Trade timestamps are now stored in UTC. Hour-of-day, weekday, overtrading, and equity-by-day analytics group trades using the account's broker timezone. Trading sessions (Asian, London, New York) use IANA timezone definitions with automatic daylight-saving handling. Implements ADR-005.
- Rebuilt economic calendar with USD high-impact events for 2025-2026 (added PPI, Retail Sales, ISM Services PMI)
- Fixed DST handling: event times now reflect actual UTC per date
- Asymmetric matching window: 30 min before event, 60 min after
- AI Coach analysis now renders standard markdown: headings, bold, italic, lists, horizontal rules, tables, blockquotes, inline and fenced code. Dollar amounts retain their color coding (negative red, positive green).

### Security
- AI Coach output is now rendered through a safe markdown parser. Hardens the rendering layer against unsafe HTML in model output.

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
