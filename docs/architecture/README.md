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

## Related

- `../plan/` — what's being worked on (`tasks.md`), what's queued (`todo.md`), what needs human action (`manual-tasks.md`)
- `../runbooks/` — step-by-step ops procedures (DB restore, logging setup, tool inventory)
- `../reviews/` — historical audits by date (useful for "when did we decide X?")
