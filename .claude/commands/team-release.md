---
description: Multi-agent release validation — 4 specialists check in parallel, then Opus synthesizes into go/no-go decision.
---

# Team Release

Use the **team-release** agent for this task. This orchestrates 4 specialist validators in parallel for comprehensive release readiness check.

Delegate all work to the `team-release` agent now.

## What it does

1. **Phase 1** — Launch 4 validators in parallel:
   - Build validator (frontend/backend build, lint, bundle size)
   - Test runner (full test suite, coverage analysis)
   - Migration checker (Alembic safety, reversibility, model alignment)
   - API contract checker (breaking changes, frontend-backend consistency)

2. **Phase 2** — Collect and validate all check outputs

3. **Phase 3** — Release synthesizer (Opus) makes go/no-go decision + generates release notes

4. **Phase 4** — Output decision with blockers/conditions

## Output

- `docs/reviews/release/summary.md` — release decision + release notes
- `docs/reviews/release/*.json` — individual check outputs
