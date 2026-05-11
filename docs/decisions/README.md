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
