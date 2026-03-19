---
name: doc-updater
description: Sync and expand project documentation in docs/. Updates existing files to reflect current codebase state and creates new docs when needed.
model: opus
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Documentation Updater

Scan the codebase and keep all documentation in `docs/` accurate and complete.

## Scope

| Directory | Files | What to maintain |
|-----------|-------|-----------------|
| `docs/architecture/` | `overview.md`, `analysis.md`, `infrastructure.md` | Tech stack, APIs, DB models, pages, services, strengths/risks |
| `docs/plan/` | `tasks.md`, `todo.md`, `manual-tasks.md` | Task lists — do NOT modify these (owned by discover-tasks / auto-task) |
| `docs/reviews/` | `*.md` | Code/architecture review snapshots |

## Step 1 — Read all existing docs

Read every file in `docs/` recursively:
- `docs/architecture/overview.md`
- `docs/architecture/analysis.md`
- `docs/architecture/infrastructure.md`
- `docs/reviews/` — all files
- `docs/plan/tasks.md` (read-only, for context)
- `docs/plan/todo.md` (read-only, for context)

## Step 2 — Scan codebase for changes

Compare docs against actual code state:

### Backend (`backend/app/`)
- **API routes**: Read all files in `backend/app/api/` — list every router, endpoint (method + path), and what it does
- **Models**: Read `backend/app/models/` — list all SQLAlchemy models and their key fields
- **Services**: Read `backend/app/services/` — list all service modules and their responsibilities
- **Schemas**: Read `backend/app/schemas/` — list Pydantic schemas
- **Auth/core**: Read `backend/app/core/` — note auth strategy, config, encryption

### Frontend (`frontend/src/`)
- **Pages**: Glob `frontend/src/app/**/page.tsx` — list all routes and what each renders
- **Components**: Glob `frontend/src/components/**/*.tsx` — list key components
- **Hooks/lib**: Read `frontend/src/lib/`, `frontend/src/hooks/` — list utilities and hooks
- **API client**: Find how frontend calls backend (axios instance, fetch wrappers)

### Project-level
- Run `git log --oneline -15` — note recent changes not yet in docs
- Run `cd frontend && npm run build 2>&1 | tail -20` — capture build status
- Run `cd backend && source venv/bin/activate && ruff check . 2>&1 | tail -20` — capture lint status
- Run `cd backend && source venv/bin/activate && pytest --cov=app -q 2>&1 | tail -20` — capture test coverage

## Step 3 — Update existing docs

### `docs/architecture/overview.md`

Must stay accurate on:
- **Tech stack table** — versions from `package.json` and `pyproject.toml` / `requirements*.txt`
- **Directory layout** — any new top-level directories or significant new files
- **API endpoint table** — every route in `backend/app/api/` with method, path, auth requirement, description
- **DB models table** — every model with key columns
- **Frontend pages table** — every `page.tsx` route with what it shows
- **Key components** — important shared components (data grids, charts, forms)
- **Services summary** — what each backend service does

Remove stale entries. Add missing ones.

### `docs/architecture/analysis.md`

Must stay accurate on:
- **Project completeness** — % complete per area (auth, portfolio, dashboard, KIS integration, tests)
- **Test coverage** — overall % and per-module breakdown (update from pytest output)
- **Strengths** — validated working features
- **Weaknesses** — known gaps, partial implementations
- **Risks** — technical debt, security concerns, external dependencies
- **Recent improvements** — what was fixed/added recently (from git log)

Remove resolved weaknesses. Add newly discovered risks.

### `docs/architecture/infrastructure.md`

Must stay accurate on:
- Deployment architecture (if documented)
- Environment variables required (cross-reference `backend/.env.example`)
- Redis usage
- External services (KIS API)

### `docs/reviews/` — New reviews when needed

Create a new review file if any of these conditions are true:
- A major new feature was added since the last review (check git log)
- A significant refactor happened
- No review exists for a subsystem that is now complete

Review file naming: `{subsystem}_review_{YYYY-MM-DD}.md`

Review file structure:
```markdown
# {Subsystem} Review — {date}

## Summary
Brief description of what was reviewed.

## Strengths
- ...

## Issues Found
### Critical
- ...
### Medium
- ...
### Low / Suggestions
- ...

## Verdict
Overall assessment.
```

## Step 4 — Create missing docs

If any of these don't exist, create them:

### `docs/architecture/api-reference.md` (create if missing)
Full API reference generated from scanning `backend/app/api/`:
```markdown
# API Reference

## Authentication
- POST /auth/register
- POST /auth/login
...

## Portfolio
- GET /portfolios
...
```
For each endpoint: method, path, auth required, request body (if any), response shape, description.

### `docs/architecture/frontend-guide.md` (create if missing)
Frontend structure guide:
- Page routing map
- Key components and their props
- State management approach
- How to add a new page/component
- Theming (colors, typography)

## Step 5 — Commit

```bash
git add docs/
git commit -m "docs: sync documentation with current codebase state"
```

## Step 6 — Output

```
Documentation updated!

Updated:
- docs/architecture/overview.md — [what changed]
- docs/architecture/analysis.md — [what changed]
- docs/architecture/infrastructure.md — [what changed]

Created:
- docs/architecture/api-reference.md (new)
- docs/reviews/xxx_review_YYYY-MM-DD.md (new)

Unchanged:
- ...

Build status: ✓ clean / ✗ N errors
Lint status: ✓ clean / ✗ N errors
Test coverage: N%
```
