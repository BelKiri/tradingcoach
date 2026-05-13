# ADR 001: Backend deployment via Docker Compose

Status: Accepted

Date: 2026-05-11

## Context

Backend (Python 3.11 + FastAPI) needs to run on the self-managed VPS

chosen in ADR-003. Server is provisioned with hardening complete (non-root service user, UFW, fail2ban, Docker installed via cloud-init),

but application code is not yet deployed.

Docker was installed by default via the cloud-init snippet without an

explicit deployment-method decision. Before the deploy task starts,

the choice between Docker and bare-metal (systemd + venv) needs to be

made deliberately and recorded.

Two viable patterns exist:

- Docker containers orchestrated by `docker compose`

- systemd service running Python in a venv directly on host

A parallel project (OnboardLens) will require an n8n stack on the same

server within ~5 days, which makes multi-service orchestration a

near-term requirement, not a hypothetical one.

## Decision

Deploy backend as Docker containers orchestrated by `docker compose`.

Single `docker-compose.yml` at repo root will define:

- `api` service — FastAPI on port 8000

- Shared `.env` file

- Docker network for future additions (n8n for OnboardLens, scrapers,

  monitoring, etc.)

Operational commands:

- Logs: `docker compose logs -f`

- Restart: `docker compose restart`

- Deploy: `git pull && docker compose up -d --build`

**Note:** Telegram bot is deprecated (the product moved to web-only

because dashboards with trade analytics cannot be presented in Telegram).

No `bot` service is included in compose. Bot code remains under

`tradecoach/bot/` as dead code until a separate cleanup task — its

presence does not affect deployment.

## Alternatives considered

**1. systemd + venv (rejected)**

Lower memory overhead, simpler for single-process setup, no Docker layer

to debug. Rejected because:

- Parallel n8n stack for OnboardLens within ~5 days requires Docker

  Compose anyway — running both patterns side by side would be worse

- Reproducibility weaker: server drift between dev (Mac) and prod (Linux)

- Weaker senior signal — bare systemd is fine for hobby projects,

  Docker Compose is the production-grade pattern

**2. Docker without Compose, plain `docker run` (rejected)**

Simpler initial setup, one less tool. Rejected because:

- Every deploy becomes a custom shell script

- No declarative service definition

- Hard to add additional services later without rewriting deploy flow

- Compose chosen even though only one service (api) runs today, because

  n8n is coming within days — single-service compose now → multi-service

  later without architectural change

**3. PaaS (Railway, [Fly.io](http://Fly.io)) (rejected earlier)**

See ADR-003 for the hosting-level decision that ruled out PaaS.

## Consequences

**Positive:**

- Multi-service stack (api + future n8n + future services) becomes

  trivial — add a block to compose.yml

- Reproducible: `docker compose up` works identically on dev and prod

- Standard production pattern — easy to onboard contractors later

- Clean isolation of the API process from host (deps, Python version,

  system libraries all containerized)

- Easy rollback: `git checkout <prev-sha> && docker compose up -d --build`

**Negative:**

- ~100–200 MB additional memory overhead vs bare venv (acceptable on

  the chosen VPS instance)

- One more abstraction layer when debugging unusual issues

- Need to maintain `Dockerfile` and `docker-compose.yml` as code evolves

- Initial setup cost ~1 hour vs ~15 min for a systemd unit

**Follow-up tasks (not part of this ADR):**

- Create `Dockerfile` for the FastAPI backend

- Create `docker-compose.yml` at repo root

- Define `.env` management strategy for production secrets (likely

  manual upload to server, not in git — to be confirmed in deploy task)

- Bot deprecation cleanup (remove `tradecoach/bot/`, related tests,

  bot-only deps) — future cleanup task, not blocking deploy

- Future ADR: backup strategy for Docker volumes

- Future ADR: domain + HTTPS reverse proxy (Caddy vs nginx + certbot)
