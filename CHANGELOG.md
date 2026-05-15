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

### Changed
- Trade timestamps are now stored in UTC. Hour-of-day, weekday, overtrading, and equity-by-day analytics group trades using the account's broker timezone. Trading sessions (Asian, London, New York) use IANA timezone definitions with automatic daylight-saving handling. Implements ADR-005.
- Rebuilt economic calendar with USD high-impact events for 2025-2026 (added PPI, Retail Sales, ISM Services PMI)
- Fixed DST handling: event times now reflect actual UTC per date
- Asymmetric matching window: 30 min before event, 60 min after

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
