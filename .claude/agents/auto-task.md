---
name: auto-task
description: Implement all incomplete items in docs/plan/tasks.md sequentially. If tasks.md is empty, promote next milestone from todo.md.
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
---

# Auto Task

Process all incomplete items in `docs/plan/tasks.md` from top to bottom.

## Pre-step: When tasks.md is empty

1. Read `docs/plan/tasks.md`
2. If **zero** incomplete items (`[ ]`):
   - Read `docs/plan/todo.md`
   - Select actionable items from the first incomplete milestone
   - Break each into single-commit-sized tasks and write to `tasks.md`
   - Clean up completed items (`[x]`) if 10+ have accumulated
   - Commit: `docs: promote tasks from todo.md milestone N`
3. If incomplete items exist → enter execution loop directly

### Promotion rules

**Promote to tasks.md:**
- Items implementable with current codebase (no external deps)
- Items not requiring API keys, service signups, or manual steps
- Decomposed to single-commit size

**Do NOT promote:**
- Large architecture changes
- Items requiring user action → add to `manual-tasks.md`
- Items with unmet prerequisites

## Execution loop

Repeat until no `[ ]` items remain:

### Each iteration:

1. **Read `docs/plan/tasks.md`**
   - Count remaining `[ ]` items
   - If none → exit loop, print completion message

2. **Implement next item** (same as `/next-task`)
   - Implement only the first `[ ]` item
   - Follow project rules (types, immutability, file size limits)
   - Do not touch other items

3. **Update tasks.md**
   - Mark completed: `[ ]` → `[x]`

4. **Update related docs** (only if changed, skip if no diff needed):
   - `docs/architecture/overview.md` — API, DB models, pages, services, tech stack changes
   - `docs/architecture/analysis.md` — strengths/weaknesses, risks, completeness changes
   - `docs/plan/todo.md` — check off promoted items, add newly discovered future work
   - `docs/plan/manual-tasks.md` — add user-action items, remove completed ones

5. **Commit**
   ```
   git add -A
   git commit -m "<type>: <summary under 70 chars>"
   ```

6. **Print progress**
   ```
   [done] Completed: <item>
   [next] Next: <next item>
   [remaining: N]
   ```

7. Continue to next iteration

## Stop conditions

Stop immediately and notify user if:

- No `[ ]` items remain → normal completion
- Implementation error (build fail, type error, missing dep) → print error + completed items so far
- Same item fails 2+ times → stop and report (do not ask to skip)

## Completion output

```
All tasks complete!

Completed: N items
Commits: N

Done:
- [x] item 1
- [x] item 2
...

Next: run `/discover-tasks` to find new work.
```
