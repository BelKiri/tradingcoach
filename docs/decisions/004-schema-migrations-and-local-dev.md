# ADR 004: Schema migrations and local development environment

Status: Accepted Date: 2026-05-14

## Context

Until now the project had no separate development environment. The codebase reads a single database URL per deployment, with no dev/prod switch, and the only database that existed was the production one. The database schema was not under version control anywhere — table shapes were only implied by the application's data models, and structural changes were applied directly to the hosted database.

This became a blocker. Verifying behaviour on realistic data requires a place where writes are safe. Writing test data into the production database, or relaxing the read-only guard on the production database connection used by tooling, were both unacceptable — especially with an invite-only cohort approaching, where the first users' experience must not be polluted by test artifacts.

Two gaps had to be closed together: there was nowhere safe to write, and there was no versioned source of truth for the schema.

## Decision

1. The database schema is now versioned as migration files in the repository. The existing production schema was captured into migrations as the starting point, so the repo holds an accurate, reviewable history of the schema going forward.
2. The project uses a local development environment, run via the Supabase CLI on the developer's machine, fully isolated from the production database. This is the write-safe environment for verification and development work.

## Alternatives considered

- **A separate hosted development project.** A second hosted project acting as dev/staging. Rejected for now: it adds another hosted environment and another set of credentials to manage, which is overhead a solo-developer project at this stage does not need.
- **Database branching on the existing project.** Branching within the single existing project. Rejected for now: it depends on plan tier and adds a workflow to learn, for a benefit (shared remote dev) that a local environment already provides at this stage.
- **A local environment via the Supabase CLI.** Chosen. Free, isolated from production by construction, and sufficient for the current need — a write-safe place to verify behaviour. The schema-as-migrations decision came out of this naturally: standing up a local database requires the schema as code.

## Consequences

- The repository now carries the schema as migrations. Future structural changes go through migration files rather than being applied ad hoc, which keeps the schema reviewable and reproducible.
- There is a write-safe local environment, which unblocks verification work that could not previously be done without touching production.
- The local environment is not a full staging environment. It runs on one developer's machine, is not shared, and does not exercise hosted infrastructure (reverse proxy, hosting, networking). If a shared remote pre-production environment is needed later — for example when more than one person works on the project, or when hosted-infra behaviour must be tested — that is a separate decision to revisit, and one of the alternatives above would come back into scope.
- Tooling that connects to the production database stays read-only. The local environment is where writes happen; production access remains restricted.

