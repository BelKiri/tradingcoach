# ADR 006: Canonical domain migration — apex form and CORS transition

Status: Accepted Date: 2026-05-17

## Context

Ahead of the first invite-only cohort, the TradingCoach frontend migrated from its legacy preview URL (assigned by the hosting provider) to a custom domain, `trading-coach.app`. The migration involved two coupled decisions that this ADR records together because they belong to the same operation and were taken with the same horizon in mind.

**Decision 1 — domain form.** The custom domain has two viable production URL shapes: the apex `trading-coach.app` and the `www.trading-coach.app` subdomain. Both resolve to the same deployment. The canonical choice determines what users see in the address bar and in invite links, the direction of the 308 redirect, the Site URL configured in the authentication provider, and the primary origin in the backend CORS allowlist.

The frontend hosting provider's documented recommendation is to use `www` as canonical, on the grounds that `www` natively supports `CNAME` records and is resilient to changes in the provider's serving IPs. Apex requires either CNAME flattening at the DNS layer or A records pointing at fixed IPs.

**Decision 2 — CORS allowlist transition.** The legacy preview URL had been the public-facing frontend for months. Prospective users had bookmarks and shared links pointing at it. Two patterns were available for the backend CORS allowlist: replace the legacy origin with the canonical ones cleanly, or admit both during a bounded transition window.

This decision was implemented during Task 028.

## Decision

**Domain form.** Apex `trading-coach.app` is canonical. `www.trading-coach.app` issues a 308 permanent redirect to apex.

**CORS allowlist.** Additive. The legacy preview URL remains admitted alongside the new canonical origins (apex, `www`) and localhost. A separate cleanup task is scheduled in the post-cohort backlog to remove the legacy entry once the cohort has been stable on the canonical domain for approximately one week.

## Alternatives considered

**Use** `www` **as canonical (the provider's recommended path).** Rejected. The portability argument is real but speculative — recovering from a hypothetical future serving-IP change at the hosting provider is one DNS record update, a one-time minutes-of-work event. The aesthetic cost of `www` in user-facing surfaces (invite links, address bar, support emails) is paid continuously by every user.

**Treat both forms as canonical with no redirect.** Rejected. Splits authentication and SEO surface, doubles the configuration matrix in the auth provider (Site URL is single-valued), and creates ambiguity for users bookmarking one form and sharing the other.

**Replace the legacy origin cleanly in CORS.** Rejected. Anyone hitting the legacy preview URL after the change would see the frontend load — the preview deployment is still live — but every backend call would fail at the CORS preflight, presenting as broken authentication, broken trade import, broken AI Coach. A frustrating partial outage with no clear signal to the user that the fix is "use a different URL." For a pre-revenue product preparing its first invite-only cohort, the cost of confusing the small number of users who still have the legacy URL bookmarked is disproportionate to the benefit of an immediately clean allowlist.

**Permanent dual CORS support.** Rejected. The legacy preview URL is provider-assigned and tied to a no-longer-canonical name; carrying it forever is technical debt and a future source of confusion. The transition window is bounded.

## Consequences

- DNS: apex resolves via CNAME flattening at the DNS provider, configured in DNS-only mode (no proxying). `www` is a CNAME at the hosting provider with a redirect rule pointing at apex.
- Auth provider Site URL is set to the apex form. The `www` and legacy preview forms are in the Redirect URLs list to handle the redirect chain on first sign-in and to keep the legacy form working during transition.
- TLS is auto-issued for all forms by the hosting provider. The `.app` TLD is HSTS-preloaded, so non-HTTPS access is blocked at the browser level regardless of the redirect chain.
- Backend CORS allowlist temporarily admits three production origins (apex, `www`, legacy preview) plus localhost. The list shrinks back to two production origins after cleanup.
- Cleanup trigger: approximately one week of stable cohort usage on the canonical domain, with no support reports of users hitting the legacy URL. The exact removal date is the user's call, not a hardcoded deadline. The cleanup task carries a forward reference to this ADR.
- If the hosting provider changes its serving IPs in a way that breaks CNAME flattening, recovery is updating one DNS record. The trade is accepted explicitly.

A future contributor reading the hosting provider's documentation may propose switching the canonical form to `www`, or may see the legacy preview URL in the CORS list and assume it is dead config. This ADR is the answer to both: the apex preference is intentional and paid for in continuous user-facing aesthetic; the legacy CORS entry is intentional and time-bounded, with its cleanup explicitly scheduled, not forgotten.