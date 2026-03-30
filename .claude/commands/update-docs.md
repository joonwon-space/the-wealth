---
description: Sync all docs/ files with current codebase state. Extracts ground truth from code first, diffs against docs, then updates only what changed.
---

# Update Docs

Use the **doc-updater** agent for this task.

Delegate all work to the `doc-updater` agent now.

## What this command does

1. **Extracts ground truth from code** using bash/glob/grep — never relies on AI memory:
   - All backend routes (method + full path) from `backend/app/api/`
   - All frontend pages from `frontend/src/app/**/page.tsx`
   - All DB models from `backend/app/models/`
   - Recent git changes (`git log --oneline -20`)

2. **Reads all docs** in `docs/architecture/`

3. **Builds an explicit diff** — two lists per doc section:
   - Items in code but missing from docs → add
   - Items in docs but not in code → remove

4. **Updates docs** based on the diff — does not rewrite sections that are already accurate

5. **Creates missing docs** if `api-reference.md` or `frontend-guide.md` don't exist

6. **Commits** all doc changes with a diff summary in the output

## What this command does NOT touch

- `docs/plan/tasks.md` — owned by `/auto-task` and `/next-task`
- `docs/plan/todo.md` — owned by `/discover-tasks`
- `docs/plan/manual-tasks.md` — owned by `/discover-tasks`
- Source code — documentation only

## When to run

- After implementing a significant feature or milestone
- When docs feel stale or out of sync with reality
- Before a code review or architecture discussion
- Periodically (e.g. once per milestone)

## Why ground truth extraction matters

**Previous approach**: AI reads docs + code → notices discrepancies → updates.
**Problem**: LLMs miss things when comparing mentally. New endpoints, pages, or features silently get skipped.

**New approach**: Extract full list from code first → explicit diff → patch only the gaps.
This guarantees nothing is missed regardless of how many files changed since the last docs update.
