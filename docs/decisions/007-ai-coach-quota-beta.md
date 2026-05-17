# ADR 007: AI Coach quota during MVP beta

Status: Accepted Date: 2026-05-17

## Context

The AI Coach feature generates a per-trade-history coaching session using a large language model. Each session has a non-trivial unit cost (LLM tokens at current pricing) and is the primary product surface that this beta exists to validate. Going into the first invite-only cohort, the product needs a quota policy that:

- Bounds total LLM spend for the beta within a pre-allocated budget.
- Gives each invited user enough opportunities to evaluate the product across the realistic shape of their trading.
- Avoids enabling unbounded re-analysis of the same data while the analysis engine itself is still being improved.
- Is simple enough to explain to a user in one sentence and to enforce with a small amount of code.

The product is pre-revenue. No payment surface is in place. There is no Stripe integration, no subscription tier, no soft-degrade path. The quota is, in effect, a hard limit during beta.

## Decision

Two coupled caps, both enforced server-side before any LLM call:

1. **Lifetime cap, per user: three coaching sessions total during beta.** Tracked on a counter column on the user row, incremented atomically after a successful generation, rolled back if the increment loses a race.
2. **Per trading account cap: one coaching session per account.** A user may generate at most one session for each trading account they connect.

A bypass flag exists on the user row, used by the operator account only during development and verification. It is not handed to users.

When either cap is exceeded, the API returns HTTP 403 with an informative message pointing the user to a contact channel for expanded access. There is no paywall, no soft tier, no partial coaching output.

## Alternatives considered

**Lower cap (one or two sessions).** Rejected for the beta. The target audience for the cohort is active retail traders who typically trade through multiple brokers. A single session would let a user evaluate the product on one account's history, which is not representative of how they actually trade. The product's behavioural-pattern detection needs to be tried against the trader's full footprint to be fairly evaluated.

**Higher cap (five or more sessions).** Rejected. Pushes total beta LLM spend outside the pre-allocated budget envelope and creates pressure to re-analyse the same account multiple times — which the analysis engine does not yet handle well (see "per-account cap" rationale below).

**Per-account cap higher than one — for example, three per account.** Rejected for the current beta. The current analysis path is designed around a single ingestion of a trading history per account. When a user adds new trades to an account that has already been analysed, the model does not currently produce a high-quality differential analysis — it largely repeats prior conclusions. Allowing multiple sessions per account before that limitation is fixed would deliver low marginal value at full LLM cost. This is a known limitation, scheduled for rework. The per-account cap will be revisited when incremental analysis lands.

**Per-day or per-month rolling quota.** Rejected for the beta. Adds time-keeping complexity, invites users to "wait it out" rather than form an opinion, and does not match the underlying constraint, which is total spend, not request rate.

**No cap, soft monitoring only.** Rejected. Unbounded LLM spend during an invite-only beta with no payment surface is not a position the project will be in.

**Per-account cap aligned with the maximum number of trading accounts a user may register.** This is the shape of the current design — the beta allows up to three trading accounts per user, and one session per account, so the per-account cap and the lifetime cap converge on three for a fully-onboarded user. Recorded as a property of the current design, not as an independent decision: the per-account cap is driven by the analysis-quality constraint above, and the trading-accounts cap is set elsewhere; their numerical coincidence is incidental for the beta and may diverge later.

## Consequences

- Total beta LLM cost is bounded by a known function of cohort size and is reviewed against the allocated budget before the cohort is expanded.
- The user-facing message is clear: hitting the cap returns a 403 with a specific reason and a contact path for expanded access. Users do not experience silent failures or degraded output.
- The bypass flag is operator-only. It is not a product feature; it exists to allow internal verification without consuming production quota. If the cohort later includes invited users who need elevated limits before the post-beta lift, those exceptions are granted out-of-band, not by widening the bypass flag's audience.
- Post-beta, the cap is expected to lift in some form — either raised wholesale, replaced with paid-tier limits, or both. The shape of the post-beta quota is not decided in this ADR; it depends on feedback from the cohort, on the analysis-quality work landing, and on whether a payment surface is in place by then.
- A future contributor may see the lifetime cap of three and the per-account cap of one and propose "rationalising" them — for example, dropping the per-account cap as redundant given the lifetime cap. This ADR is the answer: the per-account cap is a separate constraint driven by current analysis quality, not a fence around the lifetime cap. It is scheduled to be revisited on its own merits.
- The contact channel referenced in the error message is operator-controlled and may change. The message text is not part of this decision; the policy is.

