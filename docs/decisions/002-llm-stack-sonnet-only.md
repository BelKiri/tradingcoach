# ADR 002: LLM stack — single-model Claude Sonnet 4.6

Status: Partially Implemented

Date: 2026-05-11

## Context

Current production code in `tradecoach/services/llm.py` uses two models

behind a router:

- `claude-sonnet-4-20250514` (outdated Sonnet snapshot) for deep
  analysis (coaching, full reports)
- `gpt-4o-mini` (OpenAI) for fast/quick queries and classification-style
  helpers

Both choices were made before Anthropic released Claude Sonnet 4.6 and

Haiku 4.5. The router was designed when a `/check` pre-trade command

existed (fast inference path) — that feature has since been removed

from MVP, leaving the router with no real-world quick-path use case.

The actual product workflow is:

1. Trader uploads trades
2. Backend computes ALL math and behavioral classification
  programmatically in `trade_analyzer.py` (no LLM involved)
3. Backend assembles a rich structured context (50 recent trades +
  behavioral tags + session/pair breakdowns + revenge/martingale/
   overtrading sequences + future: macro events, indicators)
4. LLM is called ONCE to convert that structured context into a
  human-readable coaching insight

There is no remaining task in the pipeline that benefits from a fast,

cheap classification model. All classifications are already Python.

No users yet — this is the cheapest possible moment to clean up the

LLM stack.

## Decision

Migrate to **Claude Sonnet 4.6 as the single LLM** for all generation

tasks (coaching insights, full reports, any classification-style

helpers that may emerge).

Drop:

- `claude-sonnet-4-20250514` — outdated snapshot
- `gpt-4o-mini` — no remaining product use case
- `openai` dependency from `requirements.txt`
- OpenAI-related env vars in `tradecoach/config.py`
- LLM router logic in `llm.py` `quick_query`, `route_query`, QueryType
  routing) — single model means no routing needed

Single vendor (Anthropic), single model (Sonnet 4.6), single code path.

## Alternatives considered

**1. Keep current stack (Sonnet snapshot + gpt-4o-mini) (rejected)**

Zero migration work. Rejected because: pinned Sonnet snapshot will

eventually deprecate, dual-vendor adds operational overhead (two API

keys, two billing dashboards, two failure modes), and outdated snapshots

underperform modern models on long-context trading prompts.

**2. Sonnet 4.6 + Haiku 4.5 with router preserved (rejected)**

Two-model setup mirroring the current quick/deep split, just with newer

models. Rejected because: there is no real product use case for Haiku

in TradingCoach. All classification work (behavioral patterns, session

analysis, risk detection) is algorithmic Python, not LLM. The remaining

LLM job — generate coaching insights from pre-computed structured

context — always needs Sonnet-tier quality and depth. Adding Haiku

would mean maintaining a router, two prompt styles, two cost models,

and two sets of regression tests, for no quality benefit.

**3. Sonnet 4.6 only, keep `gpt-4o-mini` for legacy quick path

(rejected)**

Slightly cheaper than Haiku for trivial calls. Rejected for the same

reason as #2 plus dual-vendor overhead — strictly worse than #2.

**Future re-evaluation:** if a feature emerges that genuinely needs

fast/cheap inference (real-time chat with trader, high-volume

pre-screening, batch classification at scale beyond what Python can

handle), add Haiku 4.5 (or whatever is current at the time) in a new

ADR. YAGNI for now.

## Implementation status (2026-05-12)

Partially implemented in production hotfix.

- Done: model migrated to current Sonnet 4.6
- Pending: removal of dual-vendor router code and OpenAI dependency

## Consequences

**Positive:**

- One vendor, one API key, one billing dashboard
- Modern model with better trading-context understanding
- Removes router complexity from `llm.py` — single code path simpler
  to test, debug, and reason about
- Easier cost forecasting (one per-token rate)
- Removes `openai` Python dependency entirely
- Aligns with the product reality (no Telegram bot, no `/check`
  command, no fast-path needs)

**Negative:**

- Slightly higher per-call cost than if a Haiku path existed for trivial
  helpers — acceptable trade-off, volumes too low to matter (zero users
  today, projected $1–2/user/month at MVP volumes)
- One-time migration work in `tradecoach/services/llm.py`
- Vendor lock-in to Anthropic (acceptable: product fit is strong,
  switching cost is a single-file rewrite if ever needed)
- Will need to re-verify coaching output quality on real Supabase data
  after migration

**Follow-up tasks (not part of this ADR):**

- Replace `deep_analysis` model ID with current Sonnet 4.6 model string
  in `tradecoach/services/llm.py`
- Remove `quick_query` function and `route_query` / QueryType routing
  from `llm.py`
- Update any callers in `coaching.py`, `report_generator.py`, etc., to
  use the simplified single-model interface
- Remove `openai` from `requirements.txt`
- Remove OpenAI-related env vars `OPENAI_API_KEY`, etc.) from
  `tradecoach/config.py`
- Re-run coaching tests against the real 81-trade Supabase dataset to
  verify output quality didn't regress
- Update cost-tracking constants in `llm.py` with current Sonnet 4.6
  per-token rates

