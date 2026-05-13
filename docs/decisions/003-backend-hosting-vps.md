# ADR 003: Backend hosting on self-managed VPS

Status: Accepted

Date: 2026-05-11

## Context

`project_brief.md` (March 2026) originally planned PaaS at

~$5–10/month. After evaluation, that decision was reversed in favour of

a self-managed VPS in EU region.

Server tier:

- Mid-tier VPS: dedicated vCPU, several GB RAM, SSD storage

- Flat monthly cost in single-digit EUR range

- Location: EU region (same network neighborhood as Supabase EU)

The server is provisioned and hardened (non-root service user, UFW,

fail2ban, Docker installed). Application not yet deployed — see ADR-001 for the

deployment-method decision.

This ADR captures the decision to leave the PaaS path, so it isn't

re-evaluated from scratch in 6 months.

## Decision

Self-managed VPS in EU region.

Hosting tier and provider are fixed for the MVP and early growth phase.

Re-evaluation trigger: when the server reaches >70% sustained CPU or

RAM, or when ops burden meaningfully impedes product work — whichever

comes first.

Deployment method on top of this VPS is defined in ADR-001 (Docker

Compose).

## Alternatives considered

**1. Railway (rejected — was the original plan)**

Zero ops overhead, push-to-deploy, integrated metrics, simple env-var

UI. Rejected because:

- Pricing scales unpredictably with usage spikes — flat-rate VPS is

  easier to budget

- Less control over networking when colocating other services (n8n

  for OnboardLens, future scrapers, monitoring stack)

- Weaker senior signal — Railway is fine, but self-managed VPS

  forces deeper understanding of the full stack and demonstrates

  production ops capability

**2. [Fly.io](http://Fly.io) (rejected)**

Better networking than Railway, edge deploys, decent free tier.

Rejected because: same cost-unpredictability concern; edge deploys

don't help a single-region MVP whose data lives in Supabase EU region

anyway.

**3. DigitalOcean / AWS Lightsail / GCP / Linode (rejected)**

Equivalent capability. Rejected because:

- The chosen provider offered the best price/performance ratio in EU

  at evaluation time

- EU data residency is a useful default for future B2B compliance

  (broker white-label use case)

- EU-region Supabase + EU VPS = same network neighborhood, low latency

**4. Larger VPS tier (rejected for now)**

Future-proof, more headroom. Rejected because: zero users, the

current tier is already overprovisioned for current load. Scale up later only if

metrics demand it.

## Consequences

**Positive:**

- Predictable flat cost in single-digit EUR range

- Full control: can colocate n8n, scrapers, future services on the

  same box at no marginal cost

- EU data residency

- Strong senior signal — real production ops experience instead of

  click-deploy abstraction

- Low latency to Supabase EU region (same network neighborhood)

- Reproducible: server provisioning via cloud-init + Docker is

  documented in code

**Negative:**

- Ops burden: manual OS updates, SSL renewal, backup strategy needed

- No managed metrics — monitoring must be added separately (Grafana,

  Uptime Kuma, or similar) as a future task

- Single point of failure — no auto-failover (acceptable for MVP, would

  revisit at meaningful revenue)

- Manual deploys `git pull && docker compose up -d --build`) until

  CI/CD is set up later

- No built-in DDoS protection beyond what the provider offers at the edge

**Follow-up tasks (not part of this ADR):**

- Domain registration + HTTPS reverse proxy (separate task)

- Backup strategy for Docker volumes and `.env` files (future ADR)

- Monitoring/alerting stack (future task — Uptime Kuma minimum)

- Automated OS security updates `unattended-upgrades`) — likely

  already configured by cloud-init, verify
