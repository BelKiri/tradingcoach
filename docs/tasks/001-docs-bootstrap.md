Окей, делаем bootstrap. Поскольку brief рассинхронизирован с реальностью, я разбил на 2 фазы: сначала структура, потом reconciliation из кода (без угадываний от меня).

---

### Task file → `docs/tasks/001-docs-bootstrap.md`

markdown

```markdown
# Task 001: Documentation infrastructure bootstrap

## Context
Repo currently has no `docs/` folder. Only `project_brief.md` at root
(dated March 2026), which is partially out of sync with current reality:
- Hosting moved from Railway (planned) → Hetzner CPX22 Falkenstein
- LLM stack changed (brief mentions GPT-4o-mini, system uses Claude
  Sonnet 4.6 + Haiku 4.5)
- Bot framework, market data providers, naming all evolved
- Vercel project name "tradeguard" differs from repo name "tradingcoach"

Without `docs/` infrastructure, the agreed workflow (PRDs, ADRs, task
files) cannot function.

## Goal
Establish minimal `docs/` skeleton + reconcile what brief says vs what
code actually does. End state: ready to write real PRD and first ADRs
in follow-up tasks.

## Out of scope
- Writing the new `docs/prd.md` content (separate task after reconciliation)
- Writing any ADR content (separate task)
- Modifying any code in `tradecoach/`, `frontend/`, `tests/`, `v0/`
- Refactoring `project_brief.md` itself

## Phased plan

### Phase 1: Create folder structure + move brief

1. Create directory tree:
   - `docs/`
   - `docs/decisions/`
   - `docs/features/`
   - `docs/tasks/`

2. Move (`git mv`) `project_brief.md` → `docs/project_brief.md`
   to preserve history. This file becomes the historical anchor —
   it will NOT be rewritten, just superseded by `docs/prd.md` later.

3. Create the following README files with short content explaining
   purpose + format. Use exactly the templates below.

   **`docs/README.md`**:
```

## TradingCoach Documentation

- `prd.md` — current product PRD (source of truth for product scope)
- `project_brief.md` — original March 2026 brief (historical, kept for context; superseded by `prd.md` where they differ)
- `decisions/` — Architecture Decision Records (ADRs)
- `features/` — per-feature PRDs for non-trivial work
- `tasks/` — implementation task files executed by Cursor Agent

```

   **`docs/decisions/README.md`**:
```

## Architecture Decision Records

Each ADR captures one decision we'll forget the reasoning for in 6 months.

### Format

File: `NNN-short-decision-name.md`

```
   # ADR NNN: [Decision]

   Status: Proposed | Accepted | Deprecated
   Date: YYYY-MM-DD

   ## Context
   [Why this decision is needed]

   ## Decision
   [What we chose]

   ## Alternatives considered
   [2-3 options we evaluated]

   ## Consequences
   [Positive and negative outcomes]
```

### When to write an ADR

- New dependency / external service choice
- Hosting / deployment changes
- Multi-table schema changes
- Auth / security model changes
- Anything where "why" matters more than "what"

```

   **`docs/features/README.md`**:
```

## Feature PRDs

One markdown file per non-trivial feature. File: `feature-name.md`.

### Write a PRD when

- Feature requires more than 2-3 days of work
- Cross-cutting changes (frontend + backend + DB)
- Architectural decision needed
- Worth discussing before building

### Skip PRD for

- Bug fixes
- Minor UI tweaks
- Dependency updates
- Copy changes

For those — direct task file in `docs/tasks/` is enough.

```

   **`docs/tasks/README.md`**:
```

## Implementation Tasks

One file per task delegated to Cursor Agent.

File: `NNN-short-name.md` (zero-padded incrementing number).

Each task contains: Context, Goal, Out of scope, Phased plan, Constraints, Output format per phase. See existing tasks for examples.

```

4. Create placeholder `docs/prd.md`:
```

## TradingCoach PRD

**Status:** placeholder — being reconciled with actual codebase in Task 001 Phase 2.

See `docs/project_brief.md` for the March 2026 brief until this file is written.

```

5. **Stop here, await user's "next" confirmation.**
   Verify with `ls -la docs/ docs/decisions/ docs/features/ docs/tasks/`
   and `git status` before stopping.

### Phase 2: Reconcile brief vs actual code

Goal: produce a fact-check report. NO new PRD writing yet — Mr.K
needs to confirm findings first.

1. Read these files for ground truth:
   - `requirements.txt` (deps actually installed)
   - `tradecoach/services/llm.py` (which LLM models, providers)
   - `tradecoach/bot/` directory (framework: aiogram vs
     python-telegram-bot — check imports)
   - `tradecoach/config.py` (env vars, providers configured)
   - `tradecoach/` top-level for market data integrations
     (twelvedata, finnhub mentions)
   - `frontend/package.json` (Next.js version, key deps)

2. Compare to claims in `docs/project_brief.md` and produce
   `docs/_reconciliation_report.md` (underscore prefix = temporary,
   will be deleted after PRD written).

   Report structure:
```

## Brief vs Code Reconciliation — Task 001 Phase 2

### Confirmed (brief matches code)

- [item]: brief says X, code confirms X

### Changed (code differs from brief)

- [item]: brief says X, code shows Y. Evidence: file:line

### Unclear (need Mr.K input)

- [item]: code shows X, but reason / timing of change not in code

### Missing from brief (in code but undocumented)

- [item]: code uses X, brief doesn't mention it

```

3. Specifically verify:
   - LLM models in use (look for "claude-sonnet", "claude-haiku",
     "gpt-4o-mini" strings)
   - Bot framework (aiogram vs python-telegram-bot imports)
   - Market data providers (twelvedata, finnhub)
   - Number of handlers in `tradecoach/bot/handlers.py` (brief says 22)
   - Number of services in `tradecoach/services/`
   - Tables / migrations if any visible

4. **Stop. Output reconciliation report path + Phase 2 summary.
   Await Mr.K review before any PRD writing.**

## Constraints (mandatory for Cursor)

- Diagnose first, show plan before any changes
- Show diff before applying ANY file modification (including new files)
- No destructive actions without explicit "yes" from user
  (the `git mv` of project_brief.md counts — confirm before doing it)
- Minimal surgical edits — no "while we're here" cleanups
- Do NOT modify `project_brief.md` content; only move it
- Test after each phase before moving to next
- If unsure between two approaches — ASK, don't guess
- Do NOT write the new `docs/prd.md` content in this task — that's
  a follow-up task after reconciliation is reviewed

## Never touch (for this task)

- `tradecoach/` — all source code
- `frontend/` — all source code
- `tests/` — all test files
- `v0/` — prototype directory
- `.env`*, `.mcp.json*`, `.gitignore`
- `requirements.txt`, `run_bot.py`, root-level `test_*.py` files
- Any code logic anywhere — this task is documentation only

## Output format per phase

After each phase, Cursor outputs:
```

Phase N complete

What was done: [bullets] Files modified/created: [list with paths] Issues encountered: [if any] Ready for next? Y/N

```

```

