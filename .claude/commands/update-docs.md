---
description: Sync all docs/ files with current codebase state. Updates existing architecture/analysis docs and creates new ones (API reference, frontend guide, reviews) when missing.
---

# Update Docs

Use the **doc-updater** agent for this task.

Delegate all work to the `doc-updater` agent now.

## What this command does

1. **Reads** all existing files in `docs/architecture/`, `docs/reviews/`
2. **Scans** the codebase — API routes, DB models, frontend pages, components, services
3. **Updates** existing docs to match current code state (removes stale entries, adds missing ones)
4. **Creates** new docs when needed:
   - `docs/architecture/api-reference.md` — full endpoint reference (if missing)
   - `docs/architecture/frontend-guide.md` — frontend structure guide (if missing)
   - `docs/reviews/{subsystem}_review_{date}.md` — review snapshot for newly completed subsystems
5. **Commits** all doc changes

## What this command does NOT touch

- `docs/plan/tasks.md` — owned by `/auto-task` and `/next-task`
- `docs/plan/todo.md` — owned by `/discover-tasks`
- `docs/plan/manual-tasks.md` — owned by `/discover-tasks`
- Source code — documentation only

## When to run

- After implementing a significant feature
- Before a code review or PR
- When docs feel stale or out of sync
- Periodically (e.g. once per milestone)
