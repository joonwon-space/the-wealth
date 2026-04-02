---
description: Multi-agent code review — 4 specialists review in parallel, then Opus synthesizes into unified verdict.
---

# Team Review

Use the **team-review** agent for this task. This orchestrates 4 specialist reviewers in parallel for comprehensive code review.

Delegate all work to the `team-review` agent now.

## What it does

1. **Phase 0** — Determine review scope (git diff, changed files)

2. **Phase 1** — Launch 4 reviewers in parallel:
   - Correctness (logic errors, edge cases, data integrity)
   - Security (vulnerabilities, auth, injection, data exposure)
   - Performance (N+1 queries, re-renders, memory leaks)
   - Maintainability (readability, conventions, architecture)

3. **Phase 2** — Collect and validate all review outputs

4. **Phase 3** — Review synthesizer (Opus) merges into unified verdict

5. **Phase 4** — Output verdict with prioritized fix list

## Output

- `docs/reviews/review/summary.md` — unified review with verdict
- `docs/reviews/review/*.json` — individual reviewer outputs
