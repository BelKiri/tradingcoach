# ADR 005: Store trade timestamps in UTC, convert at edges

Status: Accepted

Date: 2026-05-15

## Context

The trade journal importer reads timestamps from MetaTrader 4 / 5 Excel exports. MT4 / MT5 exports stamp data in **broker server time**, not UTC; broker server time is a fixed timezone the broker chooses (commonly UTC+2 or UTC+3) and the trader cannot change it from the terminal.

The current importer strips timezone information from the wall-clock values and writes them to a `timestamptz` column. Postgres then tags them `+00:00` — so the column is **labeled UTC but is semantically broker-local**. The labeled / actual mismatch propagates into analytics inconsistently:

- `pnl_by_session` and `pnl_by_hour` apply `broker_timezone` as a pre-bucket shift, which would be correct only if storage were true UTC. With broker-local storage they double-shift.
- `pnl_by_day_of_week` and `detect_overtrading` do not apply `broker_timezone`. They are accidentally correct relative to the trader's calendar precisely because storage is broker-local — not by design.

External systems the product joins against — trading sessions, macroeconomic event feeds, and Twelve Data OHLC — are all UTC-anchored. Every cross-system join is wrong by the broker's offset under the current convention.

No backfill of existing rows is required for this change; the convention switch is a clean cut-over at the data layer. ADR-004 stood up the local Supabase environment that makes the implementation safely testable. Task 017 verified the inconsistency on a real journal.

## Decision

Store every trade timestamp as **true UTC** in `timestamptz` columns. Apply `broker_timezone` at exactly two edges:

1. **On import:** convert each wall-clock value from `broker_timezone` to UTC before writing.
2. **On query for user-perspective aggregations:** convert UTC back to `broker_timezone` before grouping. This applies to P&L by hour, P&L by day / day-of-week, overtrading detection, and equity curve by day.

Aggregations that match trades against external UTC-anchored systems (sessions, macro events, market data) use UTC directly with no conversion.

Trading sessions are defined by IANA timezone names (`Europe/London`, `America/New_York`, `Asia/Tokyo`) rather than fixed offsets, so daylight-saving transitions are handled automatically by the `zoneinfo` stdlib.

The rule, in one sentence: **store UTC; convert with** `broker_timezone` **only at the import edge and at user-perspective aggregation edges; use UTC directly for any external-system join.**

## Alternatives considered

**1. Keep the current convention, document it (rejected).** Declare that timestamps are "broker-local stored as `timestamptz`" and align every analytic accordingly. Rejected because every external-system join (sessions, events, market data) still needs a conversion — this trades one set of conversions for another while leaving the storage column lying about what it contains.

**2. Store both UTC and broker-local in separate columns (rejected).** Eliminates any query-time conversion. Rejected because it creates a two-source-of-truth problem: if a user later corrects their account's `broker_timezone`, one column needs backfill while the other does not. Single column with query-time conversion is cleaner.

**3. UTC storage with fixed-offset sessions (rejected for sessions).** Cheaper than IANA — no `zoneinfo` calls. Rejected because the product needs DST handled correctly out of the gate and `zoneinfo` is stdlib in Python 3.12; the cost of IANA is essentially zero.

**4. Defer the cut-over (rejected).** Cheapest in the short term. Rejected because migration cost rises sharply once trades exist in any database; doing the cut-over before that point keeps the change to a code-only deploy plus a one-time re-import, and the inconsistency is already producing wrong analytics.

## Consequences

Positive:

- Session, macro-event, and market-data matching become correct.
- Analytics follow one principle, removing the current per-function inconsistency.
- DST is handled automatically for IANA session definitions and for any user who picks an IANA `broker_timezone` (e.g. `Europe/Berlin`).
- Postgres `AT TIME ZONE` does the conversion at query time — no client-side timezone arithmetic.
- Future features that touch time have an unambiguous convention.

Negative:

- Breaking change for the storage convention. Mitigated by the cut-over approach: TRUNCATE trades followed by re-import — locally during implementation, and on production at deploy time as a separate task.
- Three analytics functions plus the session logic need refactoring.
- The frontend hint for the account-creation `broker_timezone` field should be updated to explain what the field actually means ("timezone your broker stamps your journal in" rather than "your timezone"). Separate small task.

## Implementation status

Implemented in Task 018.

Production deploy and prod-data migration follow as a separate task.

## Related

- ADR-004 — schema migrations and local dev environment (made this safely testable).
- Task 012 — `broker_timezone` passthrough at account creation (enabled the import-edge conversion).
- Task 015 — versioned schema migrations and local Supabase environment.
- Task 017 — verification that exposed the storage-convention inconsistency on a real journal.