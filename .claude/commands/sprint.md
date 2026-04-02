---
description: "Full sprint cycle: discover → implement → review → release → docs. Single command for a complete development iteration."
---

# Sprint

Use the **workflow-sprint** agent for this task. This orchestrates the full development cycle by chaining team agents.

Delegate all work to the `workflow-sprint` agent now.

## What it does

1. **DISCOVER** — `team-discover` (5 analysts + synthesizer) → tasks.md, todo.md
2. **USER GATE** — Show priorities, wait for confirmation
3. **IMPLEMENT** — `auto-task` (batch execute all tasks) → PR + merge
4. **REVIEW** — `team-review` (4 reviewers + synthesizer) → verdict
5. **RELEASE** — `team-release` (4 validators + synthesizer) → go/no-go
6. **DOCS** — `update-docs` → sync documentation

## User gates

- After discover: confirm priorities before implementing
- After release validation: confirm deploy

## Output

Sprint summary with all phase results, completed task count, and links to reports.
