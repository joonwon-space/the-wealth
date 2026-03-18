---
description: Find next incomplete task in docs/plan/tasks.md, implement it, update docs, and commit.
---

# Next Task

Pick the first incomplete item (`[ ]`) from `docs/plan/tasks.md`, implement it, mark done, and commit.

## Steps

### 1. Identify next task
- Read `docs/plan/tasks.md`
- Find first `[ ]` item
- If none → tell user to run `/discover-tasks`
- Determine which files to create/modify

### 2. Implement
- Implement directly (tasks.md IS the plan)
- Focus on this one task only — don't touch others
- Follow project rules:
  - TypeScript: explicit types, no `any`, immutable patterns
  - Python: type annotations, PEP 8, `logging` not `print()`
  - Functions < 50 lines, files < 800 lines

### 3. Update tasks.md
- Change completed item: `[ ]` → `[x]`
- Don't modify other items

### 4. Update related docs (only if relevant changes occurred):

| Doc | When to update |
|-----|----------------|
| `docs/architecture/overview.md` | API endpoints, DB models, pages, services, tech stack, directory structure changed |
| `docs/architecture/analysis.md` | Strengths/weaknesses, risks, completeness changed |
| `docs/plan/todo.md` | Future work discovered during implementation |
| `docs/plan/manual-tasks.md` | User-action items found; completed items removed |

- Skip if no changes needed (avoid unnecessary diffs)
- Include doc updates in the same commit

### 5. Commit
```
git add -A
git commit -m "<type>: <summary under 70 chars>"
```

Commit types: `feat`, `fix`, `chore`, `refactor`, `test`

Print completed item and list of created/modified files.
