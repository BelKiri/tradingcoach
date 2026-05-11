```markdown
# Task 002: Backend Docker deployment to Hetzner

## Context

Backend is currently NOT deployed anywhere. Old GCP VM removed.
Hetzner CPX22 (46.224.52.73, Falkenstein) is hardened and ready:
deploy user created, Docker installed via cloud-init, UFW + fail2ban
active. Application code not yet on the server.

Frontend lives at https://tradeguard-cyan.vercel.app and proxies
backend calls server-side through `frontend/app/api/proxy/[...path]/route.ts`
(no mixed-content issue — all backend calls happen from Vercel server,
not browser).

Per ADR-001: Docker Compose for deployment. Per ADR-003: Hetzner
chosen over Railway/PaaS. This task implements both.

## Goal

Backend live at `http://46.224.52.73/` (port 80 via nginx → port
8000 container) with `/health` endpoint responding. Frontend Vercel
env updated to point at new backend. End-to-end smoke test passes:
user can log in, upload a trade file, see dashboard data.

## Out of scope

- HTTPS / domain / TLS certificates (separate future task — backend
  serves HTTP only for now; mixed-content is not an issue because
  Vercel proxies server-side)
- LLM stack migration to Sonnet 4.6 (Task 003, after deploy works)
- Telegram bot deployment (deprecated, code stays in image but no
  `bot` service in compose)
- News collection refactor (Finnhub stays enabled, loop runs as-is)
- CI/CD automation (manual `git pull && docker compose up -d --build`
  for now)
- Monitoring / alerting stack (future task)
- Backup strategy (future ADR)

## Phased plan

### Phase 1: Diagnose + propose artifacts

Read-only phase. Cursor produces proposals, no files written yet.

1. Read these files for context:
   - `tradecoach/main.py` — FastAPI startup, background loops, port binding
   - `tradecoach/config.py` — env var schema, required vs optional, defaults
   - `requirements.txt` — Python deps, version pins
   - `frontend/app/api/proxy/[...path]/route.ts` — confirm exact env var
     name backend URL is read from (likely `BACKEND_URL` without
     `NEXT_PUBLIC_` since server-side)
   - `frontend/.env.example` if it exists — confirm var name there too

2. Produce a diagnostic report (paste into chat, do NOT write to file):
```

### Backend startup analysis

- FastAPI startup tasks: [list async loops, background workers]
- Port binding: [host:port from [main.py](http://main.py)]
- Required env vars (will crash without): [list from [config.py](http://config.py)]
- Optional env vars (have defaults or used conditionally): [list]
- Notes on Finnhub/news loop: [confirm it starts at line X, needs FINNHUB_API_KEY at startup]

### Frontend backend URL config

- Var name: [exact var name, e.g. BACKEND_URL]
- Used in: [file:line]
- Current value in any .env.example: [value if found]

```

3. Propose Dockerfile as code block in chat (do NOT write file yet).
   Constraints for the Dockerfile proposal:
   - Base: `python:3.11-slim`
   - Multi-stage NOT required at MVP scale — single stage is fine
   - WORKDIR `/app`
   - Copy `requirements.txt` first, install (cache layer)
   - Copy entire `tradecoach/` package
   - Copy `run_bot.py` and root-level entry if needed (verify what's
     actually the FastAPI entry — likely `tradecoach.main:app`)
   - EXPOSE 8000
   - CMD using `uvicorn tradecoach.main:app --host 0.0.0.0 --port 8000`
     (confirm exact module path during Phase 1 reading)
   - Do NOT install dev tools (pytest, etc.) — production-only deps

4. Propose `docker-compose.yml` as code block in chat (do NOT write file
   yet). Required shape:
```yaml
   services:
     api:
       build: .
       container_name: tradecoach-api
       restart: unless-stopped
       ports:
         - "127.0.0.1:8000:8000"   # loopback only, nginx fronts it
       env_file:
         - .env
       # No volumes for code — image is the artifact
```
   No networks block (single service, default bridge is fine).
   No `bot` service (deprecated per ADR-001).

5. Propose `.env` template that user will create manually on server
   (paste as code block, do NOT write file). Use placeholders, mark
   each as REAL/PLACEHOLDER/EMPTY-OK based on Phase 1 diagnostic of
   config.py:
```

## Required (real values)

SUPABASE_URL=<real> SUPABASE_KEY=<real> ANTHROPIC_API_KEY=<real> TWELVEDATA_API_KEY=<real> FINNHUB_API_KEY=<real>

## Required by [config.py](http://config.py) but feature-disabled / unused

## (use real values to avoid startup crash; values below TBD)

OPENAI_API_KEY=<keep real until Task 003 removes it> TELEGRAM_BOT_TOKEN=<real or empty-string if [config.py](http://config.py) allows> STRIPE_SECRET_KEY=<placeholder> STRIPE_WEBHOOK_SECRET=<placeholder>

## App

APP_ENV=production APP_HOST=0.0.0.0 APP_PORT=8000

```
   Mark which placeholders config.py will reject (validation errors)
   vs which it accepts.

6. **Stop. Output diagnostic + 3 proposals. Await user "next" with
   any corrections.**

### Phase 2: Create files + local build test + push

1. Show diff before creating each file.

2. Create `Dockerfile` at repo root (using Phase 1 proposal,
   incorporating any user corrections).

3. Create `docker-compose.yml` at repo root.

4. Update `.gitignore` to ensure `.env` is excluded (verify it
   already is — usually `.env`* pattern catches it; do NOT add
   `.env.example` to gitignore).

5. **Local build verification** — run `docker build -t tradecoach-test .`
   on Mr.K's Mac. Confirm image builds without errors. Do NOT run the
   container locally (Mr.K's Mac doesn't have prod .env, no need to
   smoke-test locally — server is the test environment).

6. If build succeeds → commit and push to main:
   - Commit message: `feat(deploy): add Dockerfile and docker-compose
     for Hetzner deployment per ADR-001`

7. **Stop. Output Phase 2 summary. Await user "next".**

### Phase 3: Server deployment runbook

Cursor does NOT have SSH access to Hetzner. Cursor produces an exact
runbook that Mr.K executes manually via ssh. No guessing — every command
specified.

1. Create `docs/runbooks/001-deploy-hetzner.md` with the following
   sections, filled with exact commands (deploy user is `deploy`,
   home is `/home/deploy`, target dir is `/home/deploy/tradingcoach`):

   - **First-time setup** (clone repo, create .env, first build)
   - **Subsequent deploys** (git pull + recreate)
   - **Verify health** (curl from server: `curl http://127.0.0.1:8000/health`)
   - **View logs** (`docker compose logs -f api`)
   - **Stop / restart** (`docker compose down`, `docker compose restart`)
   - **Rollback** (`git checkout <prev-sha> && docker compose up -d --build`)

   Use this skeleton:
```markdown
   # Runbook 001: Deploy TradingCoach backend to Hetzner

   Server: 46.224.52.73 (Hetzner CPX22, Falkenstein)
   User: deploy
   Project dir: /home/deploy/tradingcoach

   ## First-time setup
   [exact ssh + bash commands]

   ## Deploy update (after code changes)
   [exact commands]

   ## Verify health
   [curl + expected response]

   ## Logs / restart / rollback
   [exact commands per section]
```

2. Append to runbook a separate **"nginx + UFW setup"** section
   (one-time, executed once before first nginx-fronted request):
```

### Initial nginx + firewall setup (run once)

sudo apt update && sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/tradingcoach <<'EOF' server { listen 80 default_server; server_name 46.224.52.73;

```
   client_max_body_size 20M;  # for trade file uploads

   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 120s;  # AI coaching may be slow
   }
```

} EOF

sudo ln -sf /etc/nginx/sites-available/tradingcoach   
/etc/nginx/sites-enabled/tradingcoach sudo rm -f /etc/nginx/sites-enabled/default sudo nginx -t && sudo systemctl reload nginx

sudo ufw allow 80/tcp sudo ufw allow 443/tcp sudo ufw reload sudo ufw status verbose

```

3. Commit + push runbook:
   - Commit message: `docs(runbooks): add Hetzner deploy runbook`

4. **Stop. Output Phase 3 summary with runbook path. Await user
   "next" — at this point Mr.K executes the runbook manually on
   the server.**

### Phase 4: Frontend Vercel update + e2e smoke test

This phase is Mr.K's manual work + reporting back. Cursor stands
by for debug if errors appear.

Mr.K's tasks (sequence):
1. SSH to Hetzner, execute Phase 3 runbook "First-time setup"
   + "nginx setup" sections
2. From Mr.K's Mac: `curl http://46.224.52.73/health` — confirm
   200 OK
3. Open Vercel dashboard → Project `tradeguard` → Settings →
   Environment Variables → update `BACKEND_URL` (exact name confirmed
   in Phase 1) to `http://46.224.52.73`
4. Vercel → Deployments → redeploy latest
5. Open https://tradeguard-cyan.vercel.app — smoke test:
   - Log in
   - Upload a trade file (or open existing account)
   - Confirm dashboard loads with real data from backend
6. Report back to Cursor + Claude with results.

Cursor's role in this phase: if Mr.K pastes any error (curl fails,
Vercel returns 502, dashboard shows nothing) — diagnose root cause,
propose surgical fix, repeat. NO refactoring of unrelated code.

**Phase complete when e2e smoke test passes.**

## Constraints (mandatory for Cursor)

- Diagnose first, show plan before any changes
- Show diff before applying ANY file modification (Dockerfile,
  compose, runbook, .gitignore)
- No destructive actions without explicit "yes" from user
- Minimal surgical edits — no "while we're here" cleanups of
  `tradecoach/` or `frontend/` code
- Test after each phase before moving to next
- If unsure between two approaches — ASK, don't guess
- Do NOT modify `tradecoach/`, `frontend/`, `tests/`, `v0/` source
  code in this task. This task is deployment infra only.
- Do NOT modify `requirements.txt` (LLM stack cleanup = Task 003)
- Do NOT remove env vars from `.env.example` (sync with code = Task 003)
- Do NOT attempt SSH from local Cursor — server ops are Mr.K's manual
  work via runbook
- If `docker build` fails in Phase 2 due to a code-level issue (e.g.
  missing import, syntax error), STOP and ask Mr.K — do NOT auto-fix
  application code in a deploy task

## Never touch (for this task)

- `tradecoach/` — all Python source
- `frontend/` — all TypeScript/React code (Vercel env vars are updated
  by Mr.K manually in Vercel UI, not in code)
- `tests/` — test suite
- `v0/` — abandoned sandbox
- `requirements.txt` — locked until Task 003
- `.env.example` — locked until Task 003
- ADR files in `docs/decisions/`
- Existing `docs/` content other than adding `docs/runbooks/`

## Output format per phase

After each phase, Cursor outputs:
```

Phase N complete

What was done: [bullets] Files modified/created: [list with paths] Issues encountered: [if any] Ready for next? Y/N

```

```

