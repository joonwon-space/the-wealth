---
description: "Feature pipeline: design → implement → review → release. Pass a feature description as argument."
---

# Feature

Use the **workflow-feature** agent for this task. Pass the user's feature requirement to the agent.

The user's feature description: $ARGUMENTS

Delegate all work to the `workflow-feature` agent now, including the feature description above.

## What it does

1. **DESIGN** — `team-feature` (4 designers + synthesizer) → PRD + task list
2. **USER GATE** — Show PRD summary, wait for approval
3. **PROMOTE** — Extract tasks from PRD → tasks.md
4. **IMPLEMENT** — `auto-task` (batch execute) → PR + merge
5. **REVIEW** — `team-review` (4 reviewers + synthesizer) → verdict
6. **RELEASE** — `team-release` (4 validators + synthesizer) → go/no-go
7. **DOCS** — `update-docs` → sync documentation

## User gates

- After PRD generation: approve design before implementation

## Output

Feature delivery summary with PRD link, completed tasks, and release status.
