# Architecture Docs Index

Entry point for understanding the codebase at a high level. `CLAUDE.md` links here for the onboarding protocol; humans can read top-to-bottom.

## Files

| File | What's inside | Read when |
|------|---------------|-----------|
| [`overview.md`](./overview.md) | Purpose, monorepo layout, module boundaries, feature list, tech stack, DB model list, KIS integration surface | Getting oriented; "what does this project do?" |
| [`api-reference.md`](./api-reference.md) | Every backend route grouped by resource — method, path, auth requirement, rate limit, request/response shape | Designing a new endpoint, changing an existing one, reviewing frontend↔backend contract |
| [`frontend-guide.md`](./frontend-guide.md) | Page routing, component tree, shared hooks, state patterns, SSE/query conventions | Adding a page, refactoring a component, tracing a UI flow |
| [`infrastructure.md`](./infrastructure.md) | Docker/CI/CD, env vars, Redis key patterns, rate limits by route, security headers, JWT lifecycle, encryption | Environment setup, deployment issue, security header audit |
| [`analysis.md`](./analysis.md) | Project strengths / weaknesses / risks, milestone completion snapshot, current gap catalog | Prioritizing work; understanding context for "why this way" |
| [`cost-management.md`](./cost-management.md) | Infra cost tracking (Neon, Redis, hosting), cost projections | Budget review; right-sizing managed services |

## Onboarding Read Order

For a brand-new session that needs full project context:

1. **`overview.md`** — big picture in under 5 minutes
2. **Role-relevant file**:
   - Backend work → `api-reference.md` + `infrastructure.md`
   - Frontend work → `frontend-guide.md`
   - Ops / SRE → `infrastructure.md` + `../runbooks/`
3. **`analysis.md`** — what's already known to be rough; avoids re-discovering known issues

## Staying Fresh

These docs are derived from code, not the other way around. If you're unsure whether a doc is current:
- `git log -- docs/architecture/<file>.md` shows the last update
- Running `/update-docs` refreshes from the current codebase state
- Any claim here should be verifiable by `grep` in ~60 seconds; if not, flag it

## New Docs (Sprint 16)

| File | What's inside | Read when |
|------|---------------|-----------|
| [`getting-started.md`](./getting-started.md) | Fresh-clone → running in minutes; all env vars, DB init, Windows gotchas | First setup on a new machine |
| [`testing-guide.md`](./testing-guide.md) | pytest markers, DB isolation, MSW handlers, coverage targets, TDD checklist | Writing or debugging tests |
| [`kis-integration.md`](./kis-integration.md) | TR_ID table, rate limiter params, KIS token lifecycle, rt_cd error codes | Any KIS API work |
| [`auth-flow.md`](./auth-flow.md) | JWT access+refresh+SSE ticket sequence, Axios interceptor, session revoke | Auth debugging or changes |
| [`feature-trading.md`](./feature-trading.md) | Order lifecycle state machine, Redis locks, settlement scheduler | Trading feature work |
| [`feature-analytics.md`](./feature-analytics.md) | Monthly return/Sharpe/MDD/CAGR formulas, scheduler jobs table | Analytics feature work |
| [`security-model.md`](./security-model.md) | Threat model, AES-256-GCM, bcrypt, audit log events, unencrypted fields | Security review |
| [`database-schema.md`](./database-schema.md) | ERD (14 tables), per-table purpose, indexes, Alembic checklist | Schema changes or queries |
| [`design-system.md`](./design-system.md) | shadcn/ui base-nova, Tailwind v4 tokens, Korean market colors, cn() | UI component work |

## Runbooks

| File | What's inside | Read when |
|------|---------------|-----------|
| [`../runbooks/troubleshooting.md`](../runbooks/troubleshooting.md) | Redis/Postgres/KIS/Alembic/SSE/OOM common failures — symptom→cause→fix | Something is broken |
| [`../runbooks/deploy.md`](../runbooks/deploy.md) | CI/CD failures, rollback, hotfix process, manual Alembic, smoke checks | Deployment issues |

## Other Docs

| File | What's inside | Read when |
|------|---------------|-----------|
| [`../brand-assets.md`](../brand-assets.md) | Logo variants (mark/lockup), SVG/PNG/ICO size matrix, PWA manifest icons, `BrandLogo` component usage, build pipeline (`scripts/build-icons.mjs`) | Updating the logo, favicon, or brand colors |

## Related

- `../plan/` — what's being worked on (`tasks.md`), what's queued (`todo.md`), what needs human action (`manual-tasks.md`)
- `../runbooks/` — step-by-step ops procedures (DB restore, logging setup, tool inventory)
- `../reviews/` — historical audits by date (useful for "when did we decide X?")
