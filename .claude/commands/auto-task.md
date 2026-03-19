---
description: Implement all incomplete items in docs/plan/tasks.md sequentially. If tasks.md is empty, promote next milestone from todo.md.
---

# Auto Task

Use the **auto-task** agent for this task. The agent runs on Sonnet for efficient implementation.

Delegate all work to the `auto-task` agent now.

## Pre-step 1: When tasks.md is empty

1. Read `docs/plan/tasks.md`
2. If **zero** incomplete items (`[ ]`):
   - Read `docs/plan/todo.md`
   - Select actionable items from the first incomplete milestone
   - Break each into single-commit-sized tasks and write to `tasks.md`
   - Clean up completed items (`[x]`) if 10+ have accumulated
   - Commit: `docs: promote tasks from todo.md milestone N`
3. If incomplete items exist → continue to Pre-step 2

### Promotion rules

**Promote to tasks.md:**
- Items implementable with current codebase (no external deps)
- Items not requiring API keys, service signups, or manual steps
- Decomposed to single-commit size

**Do NOT promote:**
- Large architecture changes
- Items requiring user action → add to `manual-tasks.md`
- Items with unmet prerequisites

## Pre-step 2: Create working branch

Before implementing any task, create a dedicated branch:

```bash
BRANCH="auto-task/$(date +%Y%m%d-%H%M)"
git checkout -b "$BRANCH"
```

Save the branch name — it will be used for the PR at the end.

## Execution loop

Repeat until no `[ ]` items remain:

### Each iteration:

1. **Read `docs/plan/tasks.md`**
   - Count remaining `[ ]` items
   - If none → exit loop, go to Post-step

2. **Implement next item**
   - Implement only the first `[ ]` item
   - Follow project rules (types, immutability, file size limits)
   - Do not touch other items

3. **Build verification** (MANDATORY before every commit)

   **If any `.ts` or `.tsx` files changed:**
   ```bash
   cd frontend && npx tsc --noEmit && npm run build
   ```
   If build fails → fix immediately and re-run. Fails twice → stop and report.

   **If any `.py` files changed:**
   ```bash
   cd backend && source venv/bin/activate && ruff check . && pytest -q --tb=short 2>&1 | tail -20
   ```
   If ruff or pytest fails → fix and re-run. Fails twice → stop and report.

4. **Update tasks.md**
   - Mark completed: `[ ]` → `[x]`

5. **Update related docs** (only if changed):
   - `docs/architecture/overview.md` — API, DB models, pages, services, tech stack changes
   - `docs/architecture/analysis.md` — strengths/weaknesses, risks, completeness changes
   - `docs/plan/todo.md` — check off promoted items, add newly discovered future work
   - `docs/plan/manual-tasks.md` — add user-action items, remove completed ones

6. **Commit**
   ```
   git add -A
   git commit -m "<type>: <summary under 70 chars>"
   ```

7. **Print progress**
   ```
   [done] Completed: <item>
   [next] Next: <next item>
   [remaining: N]
   ```

8. Continue to next iteration

## Post-step: PR, merge, cleanup

After all `[ ]` items are done:

1. **Push branch**
   ```bash
   git push -u origin "$BRANCH"
   ```

2. **Create PR** targeting `main`
   - Title: `auto-task: <summary of all completed tasks>`
   - Body: list of completed tasks + note that builds were verified before each commit

3. **Wait for CI** — poll `gh pr checks` every 10s (max 10min)
   - All checks pass → proceed to merge
   - Any check fails → stop, do NOT merge, report failure to user

4. **Merge PR**
   ```bash
   gh pr merge --squash --delete-branch
   ```

5. **Switch back to main**
   ```bash
   git checkout main && git pull origin main
   ```

## Stop conditions

Stop immediately and notify user if:

- No `[ ]` items remain → normal completion (proceed to Post-step)
- Build fails twice on same task → stop, report error and items completed so far
- CI fails on PR → stop, do not merge, report which check failed
- Same task fails 2+ times → stop and report

## Completion output

```
All tasks complete!

Branch: auto-task/YYYYMMDD-HHmm
PR: #N — merged ✓
Branch deleted ✓

Completed: N items
Commits: N

Done:
- [x] item 1
- [x] item 2
...

Next: run `/discover-tasks` to find new work.
```
