---
description: Multi-agent project analysis — 5 specialists analyze in parallel, then Opus synthesizes into prioritized tasks and roadmap.
---

# Team Discover

Use the **team-discover** agent for this task. This orchestrates 5 specialist agents in parallel for comprehensive project analysis.

Delegate all work to the `team-discover` agent now.

## What it does

1. **Phase 1** — Launch 5 analysts in parallel:
   - Tech debt (code smells, dependencies, type safety)
   - UX gaps (error states, loading, a11y, responsive)
   - Security posture (OWASP, auth, encryption)
   - Performance bottlenecks (bundle, API, DB, caching)
   - Product strategy (roadmap, feature gaps, priorities)

2. **Phase 2** — Collect and combine all findings

3. **Phase 3** — Strategy synthesizer (Opus) merges, deduplicates, and prioritizes using Impact x Effort matrix

4. **Phase 4** — Updates `tasks.md`, `todo.md`, and writes synthesis report

## Output

- `docs/plan/tasks.md` — updated with high-impact, low-effort items
- `docs/plan/todo.md` — updated with new milestones and backlog items
- `docs/reviews/team-synthesis.md` — full synthesis report
- `docs/reviews/team-analysis-latest.json` — raw combined findings
