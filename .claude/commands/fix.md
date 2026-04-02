---
description: "Bug fix pipeline: diagnose → fix → review → release. Pass a bug description as argument."
---

# Fix

Use the **workflow-fix** agent for this task. Pass the user's bug description to the agent.

The user's bug description: $ARGUMENTS

Delegate all work to the `workflow-fix` agent now, including the bug description above.

## What it does

1. **DIAGNOSE** — `team-debug` (4 analysts + synthesizer) → root cause + fix plan
2. **IMPLEMENT** — Extract fix steps → tasks.md → `auto-task`
3. **REVIEW** — `team-review` (mandatory, financial app) → verdict
4. **RELEASE** — `team-release` → go/no-go
5. **DOCS** — `update-docs` → sync documentation

## Safety rules

- Review is NEVER skipped
- If fix touches sensitive paths (KIS API, auth, transactions): REQUEST CHANGES escalates to user instead of auto-fix

## Output

Bug fix summary with diagnosis link, fix details, and release status.
