# TradingCoach

AI-powered trading education platform for active retail traders.
Upload your trade journal, get coaching insights based on your
trading behavior and market context.

## Status

MVP shipped, pre-user phase. See [CHANGELOG.md](CHANGELOG.md) for
release history.

## What it does

- Parses trade journals (MetaTrader 4 CSV, Excel)
- Detects common behavioral patterns in trading psychology
- Generates AI trading coaching insights
- Matches trades against economic calendar and market context
- Persists coaching session history for follow-up analysis

## Tech stack

- **Backend:** Python 3.12, FastAPI, Docker Compose
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Database & auth:** Supabase (Postgres, Auth with Google OAuth)
- **AI:** Anthropic Claude
- **Market data:** TwelveData, Finnhub

## Architecture

Frontend on Vercel calls backend through a server-side proxy route.
Backend serves FastAPI behind nginx and processes trade data.

For architectural rationale, see [docs/decisions/](docs/decisions/).

## Local development

### Backend

Requirements: Python 3.12, Docker.

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in required values
3. Run via Docker Compose
4. Health check: `curl http://localhost:8000/health`

### Frontend

Requirements: Node.js 20+, npm.

1. `cd frontend`
2. `npm install`
3. `npm run dev`

## Configuration

Required environment variables (see `.env.example`):

- `SUPABASE_URL`, `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ANTHROPIC_API_KEY`
- `TWELVEDATA_API_KEY`
- `FINNHUB_API_KEY`

## Testing

Tests are split into unit and integration:

- Unit (mocked, fast): `pytest tests/unit/`
- Manual smoke scripts: `scripts/manual_smoke/`

## Documentation

- [Architectural decisions](docs/decisions/)
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE)
