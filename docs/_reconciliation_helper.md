# Reconciliation helper — Task 001 Phase 2

Read-only diagnostics for follow-up reconciliation. Commands run from repo root unless noted.

## 1. `contract_specs.py`

**`find . -name "contract_specs.py" -not -path "*/node_modules/*"`**

No output — file not present in the repository.

**`grep -r "contract_specs" tradecoach/ --include="*.py"`**

No output — no Python imports or references under `tradecoach/`.

**Note:** `contract_specs` appears only in `docs/project_brief.md` and prior reconciliation docs, not in application code.

## 2. `v0/` directory

**`package.json`**

- `name`: `my-project`
- `private`: `true`
- Scripts: `dev`, `build`, `start`, `lint` (standard Next.js)
- Stack: `next` `16.1.6`, `react` / `react-dom` `19.2.4`, `recharts` `2.15.0`, Radix UI, Tailwind 4, `@vercel/analytics`
- No `@supabase/*`, no `swr`, no workspace link to `frontend/`

**README**

- No `v0/README.md` (or other README under `v0/`)
- `frontend/README.md` is the default create-next-app template; it does not mention `v0/`

**Standalone vs `frontend/`**

- `v0/tsconfig.json` maps `@/*` to `./*` inside `v0/` only
- No imports from `../frontend` or `frontend/` in `v0/`
- No imports from `../v0` or `v0/` in `frontend/`
- `grep fetch\(|useSWR\(` under `v0/` — no matches
- `v0/app/page.tsx` composes local dashboard UI components only (no backend client)
- Example static copy: `v0/components/dashboard-header.tsx` hardcodes `81 trades`

**Conclusion:** `v0/` is a separate UI prototype / design sandbox, not a dependency of `frontend/` and not wired to the TradeCoach API.

## 3. Stripe

**`grep -r "stripe" tradecoach/ frontend/ --include="*.py" --include="*.ts" --include="*.tsx"`**

`tradecoach/config.py` only:

- `stripe_secret_key: str = ""`
- `stripe_webhook_secret: str = ""`

No matches under `frontend/`.

**Related checks**

- `requirements.txt` lists `stripe>=11.4.0`
- Repo-wide `import stripe` / `from stripe` — no matches in `.py` / `.ts` / `.tsx`
- Repo-wide `webhook` in `.py` / `.ts` / `.tsx` — only `stripe_webhook_secret` in `tradecoach/config.py`
- `tradecoach/main.py` — no Stripe router or webhook route
- `frontend/app/(marketing)/pricing/page.tsx` — static comparison table; CTAs link to `/signup` only (no checkout / payment session)

**Conclusion:** Stripe is configuration + dependency declaration only; no implemented webhook endpoint or payment flow in UI/backend code searched.

## 4. ChromaDB / RAG

**`grep -r "chroma\|chromadb" tradecoach/ requirements.txt`**

- `requirements.txt:17` — `chromadb>=0.6.3` (comment: `# RAG / vector DB`)
- No matches under `tradecoach/` (no imports or runtime usage)

**RAG wording elsewhere (not ChromaDB)**

- `tradecoach/services/coaching.py`, `tradecoach/api/coaching.py`, `tests/test_coaching.py` describe “RAG” as assembled coaching context from trades/stats/news/calendar — not vector DB retrieval
- `requirements.txt:39` comment references “RAG updates” next to `apscheduler`; no `apscheduler` imports in Python sources

**Conclusion:** ChromaDB is declared in `requirements.txt` only; not used in `tradecoach/` code. “RAG” in coaching is contextual data assembly, not ChromaDB.

## 5. Frontend pages (`frontend/app/`)

**Inventory:** 16 `page.tsx` files. Route groups `(marketing)` and `app` do not appear in URLs.

| Route | File | `fetch(` / `useSWR(` in page | Data source |
|---|---|---|---|
| `/` | `(marketing)/page.tsx` | none | Static marketing content |
| `/login` | `(marketing)/login/page.tsx` | none | Supabase Auth client (`signInWithPassword`, OAuth) |
| `/signup` | `(marketing)/signup/page.tsx` | none | Supabase Auth client (`signUp`, OAuth) |
| `/pricing` | `(marketing)/pricing/page.tsx` | none | Static pricing / feature matrix |
| `/tools/economic-calendar` | `(marketing)/tools/economic-calendar/page.tsx` | none | Hardcoded `events` array |
| `/tools/pip-calculator` | `(marketing)/tools/pip-calculator/page.tsx` | none | Static form UI (no calculation wiring) |
| `/tools/position-size-calculator` | `(marketing)/tools/position-size-calculator/page.tsx` | none | Static form UI |
| `/tools/drawdown-calculator` | `(marketing)/tools/drawdown-calculator/page.tsx` | none | Static form UI |
| `/app` | `app/page.tsx` | `useSWR` | `/api/accounts/{userId}` via `fetcher` → `API_BASE` (`localhost:8000` or `/api/proxy`) |
| `/app/dashboard/[accountId]` | `app/dashboard/[accountId]/page.tsx` | `useSWR` | `/api/dashboard/{userId}?…`, `/api/accounts/detail/{accountId}`; `requestCoaching` POST via `@/lib/api` |
| `/app/coaching` | `app/coaching/page.tsx` | `useSWR` | `/api/coaching/sessions/{userId}`, `/api/accounts/{userId}` |
| `/app/coaching/[sessionId]` | `app/coaching/[sessionId]/page.tsx` | `useSWR` | `/api/coaching/session/{sessionId}`, `/api/accounts/detail/{accountId}` |
| `/app/settings` | `app/settings/page.tsx` | none in page | `@/lib/api` (`fetchAccounts`, `renameAccount`, `deleteAccount`, `deleteAllUserData`) + Supabase `signOut` |
| `/app/onboarding` | `app/onboarding/page.tsx` | none in page | `@/lib/api` (`createAccount`, `uploadTrades`) |
| `/app/connect` | `app/connect/page.tsx` | none | Static `exchanges` / `propFirms` arrays; placeholder API key fields |
| `/app/checker` | `app/checker/page.tsx` | none | “Under development” overlay; blurred static form underneath |

**Not a page (related):** `frontend/app/api/proxy/[...path]/route.ts` — server-side `fetch` to backend for production API proxying.

**Client fetch path:** `frontend/lib/swr.ts` and `frontend/lib/api.ts` use `fetch` against `API_BASE` + `/api/...` paths (not in-page mocks for authenticated app routes).

## 6. Migrations

**`find . -name "*.sql" -not -path "*/node_modules/*"`**

No output — no `.sql` files in the repo (excluding `node_modules`).

**`ls -la supabase/ 2>/dev/null || echo "no supabase dir"`**

`no supabase dir`

**Conclusion:** No in-repo SQL migrations and no `supabase/` directory; schema is implied via `tradecoach/db/models.py` and Supabase table names in `tradecoach/db/queries.py` / services, likely managed outside this tree.
