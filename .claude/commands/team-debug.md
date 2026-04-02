---
description: Multi-agent bug diagnosis — 4 specialists analyze in parallel, then Opus synthesizes into root cause and fix plan.
---

# Team Debug

Use the **team-debug** agent for this task. This orchestrates 4 specialist analysts in parallel for comprehensive bug diagnosis.

Pass the user's bug description, error message, or stack trace to the `team-debug` agent. Delegate all work to the agent now.

## What it does

1. **Phase 1** — Launch 4 analysts in parallel:
   - Error trace analyst (stack trace, error origin, call chain)
   - Data flow analyst (data path tracing, transformation issues)
   - Regression analyst (git history, suspected commits)
   - Environment/config analyst (env vars, KIS API, Redis, DB config)

2. **Phase 2** — Collect and validate all diagnostic outputs

3. **Phase 3** — Debug synthesizer (Opus) cross-references findings → root cause + fix plan

4. **Phase 4** — Output diagnosis with fix steps

## Output

- `docs/reviews/debug/diagnosis.md` — root cause analysis + fix plan
- `docs/reviews/debug/*.json` — individual analyst outputs
