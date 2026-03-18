---
name: discover-tasks
description: Research project analysis docs and codebase state to refresh tasks.md (current work) and todo.md (future work).
model: opus
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Discover Tasks

Analyze current project state and discover work items to refresh task lists.

## Document roles

| Doc | Role | Content |
|-----|------|---------|
| `docs/plan/tasks.md` | **Current work** | Immediately actionable tasks. Read by `/auto-task` and `/next-task` |
| `docs/plan/todo.md` | **Future work** | Long-term backlog/roadmap. Not urgent but eventually needed |

## Steps

### 1. Read analysis docs

Read all of:
- `docs/analysis/project-overview.md` — current structure, tech stack, API list
- `docs/analysis/project-analysis.md` — strengths, weaknesses, risks, improvements, bottlenecks
- `docs/plan/tasks.md` — current task list
- `docs/plan/todo.md` — future backlog
- `docs/plan/manual-tasks.md` — manual items

### 2. Codebase research

Investigate actual code state vs docs:
- **New files/features** not yet reflected in docs
- **TODO/FIXME/HACK/XXX comments** (`grep -r "TODO\|FIXME\|HACK\|XXX"`)
- **Build/lint errors** (`npm run build`, `ruff check .`)
- **Test coverage** (if available)
- **Dependency vulnerabilities** (`npm audit`, `pip audit`)
- **git log** — recent changes needing follow-up

### 3. Update analysis docs

Based on research:
- `docs/analysis/project-overview.md` — reflect new APIs, models, pages, services
- `docs/analysis/project-analysis.md` — update completeness, strengths/weaknesses, risks. Remove resolved weaknesses, add new risks

### 4. Refresh task lists

Classify discovered work into the appropriate doc:

**Put in `tasks.md` (current work):**
- Bug fixes
- Build/lint error fixes
- Security vulnerability patches
- Quality improvements (error handling, type fixes)
- Test additions
- User-requested features

**Put in `todo.md` (future work):**
- New feature ideas
- Large refactoring
- Deployment/infrastructure
- Performance optimization
- Long-term roadmap items

### 5. tasks.md writing rules

```markdown
# THE WEALTH — Tasks

## Current work
- [ ] Task 1 — specific, actionable description
- [ ] Task 2
...
```

- Each item must be **specific** ("add dashboard skeleton" not "improve UI")
- Decompose to single-commit size
- Clean up completed items (`[x]`) when 10+ accumulate

### 6. todo.md writing rules

```markdown
# THE WEALTH — TODO

## Milestone N: Title
- [ ] Item 1
- [ ] Item 2
...
```

- Group by milestone
- Collapse completed milestones
- Mark items ready for promotion to tasks.md

### 7. Commit

```
git add docs/
git commit -m "docs: update project analysis and task lists"
```

### 8. Output

```
Research complete!

Analysis docs:
- project-overview.md: [changed/unchanged]
- project-analysis.md: [changed/unchanged]

Task lists:
- tasks.md: N current tasks (M new)
- todo.md: N future tasks (M new)
- manual-tasks.md: N manual items

Next: run `/auto-task` or `/next-task` to execute.
```
