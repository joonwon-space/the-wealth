---
description: Multi-agent feature design — 4 specialists analyze in parallel, then Opus synthesizes into PRD and task list.
---

# Team Feature

Use the **team-feature** agent for this task. This orchestrates 4 specialist agents in parallel for comprehensive feature design.

Pass the user's feature requirement to the `team-feature` agent. Delegate all work to the agent now.

## What it does

1. **Phase 1** — Launch 4 designers in parallel:
   - Product analyst (user needs, MVP scope, competitive analysis)
   - UX designer (UI structure, user flows, accessibility)
   - Backend architect (API, database, KIS integration)
   - Frontend architect (components, state, data fetching)

2. **Phase 2** — Collect and validate all design analyses

3. **Phase 3** — Feature synthesizer (Opus) merges into unified PRD with task breakdown

4. **Phase 4** — Output PRD and implementation plan

## Output

- `docs/reviews/feature/prd.md` — unified PRD with task list
- `docs/reviews/feature/*.json` — individual analyst outputs
