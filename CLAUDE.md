# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KIS(한국투자증권) API 기반 개인 자산관리 대시보드. "더리치" 앱의 UI/UX를 벤치마킹하며, 한국 증시 컬러 컨벤션(상승=빨간색, 하락=파란색)을 따른다.

## Commands

### Frontend (`frontend/`)
```bash
npm run dev      # dev server at localhost:3000
npm run build    # production build
npm run lint     # ESLint
```

### Backend (`backend/`)
```bash
source venv/bin/activate
uvicorn app.main:app --reload         # dev server at localhost:8000
alembic upgrade head                  # run migrations
alembic revision --autogenerate -m "description"  # create migration
pytest --cov=app --cov-report=term-missing        # run tests with coverage
ruff check .                          # lint Python
black .                               # format Python
```

### Adding shadcn/ui components
```bash
cd frontend && npx shadcn@latest add <component>
```

## Architecture

### Monorepo structure
- `frontend/` — Next.js 16 App Router (React 19, TypeScript, Tailwind v4)
- `backend/` — FastAPI with async SQLAlchemy + Alembic migrations
- `docs/` — architecture, plans, runbooks, reviews (see Docs Reference Map below)

### Docs Reference Map

`docs/` is **not auto-loaded**. Use `Read` when the question matches the table below.
Index: `docs/architecture/README.md` lists every file with a one-line summary.

| Looking for | File |
|-------------|------|
| System modules & big picture | `docs/architecture/overview.md` |
| API endpoint specs | `docs/architecture/api-reference.md` |
| Frontend pages / components / hooks | `docs/architecture/frontend-guide.md` |
| Deployment, env vars, Redis keys, rate limits | `docs/architecture/infrastructure.md` |
| Project strengths, weaknesses, risks | `docs/architecture/analysis.md` |
| Infra cost tracking | `docs/architecture/cost-management.md` |
| Operational procedures (backup, restore, logging, tools) | `docs/runbooks/*.md` |
| Current sprint tasks | `docs/plan/tasks.md` |
| Future backlog | `docs/plan/todo.md` |
| Items requiring user action | `docs/plan/manual-tasks.md` |
| Historical audits and reviews | `docs/reviews/YYYYMMDD-*.md` |
| Runtime alert dumps | `docs/alerts/` (owned by `/fix-alerts`) |

**Onboarding protocol** — before a new feature/fix, read in this order:
1. `overview.md` → big picture
2. File(s) directly relevant to the task (`api-reference.md` / `frontend-guide.md` / `infrastructure.md`)
3. `analysis.md` → current gaps + priorities context

**Keep docs fresh** — after significant code changes, run `/update-docs` so these files stay the source of truth.

### Frontend
- **App Router** with server components for initial SSR load optimization
- **shadcn/ui** (style: `base-nova`, baseColor: `neutral`) — components live in `src/components/ui/`
- **Path alias**: `@/` maps to `src/`
- **State**: client-side auth state; optimistic updates on mutations
- **HTTP**: Axios instance with response interceptor for JWT expiry + auto refresh token rotation
- **Data grids**: TanStack Table v8 for holdings table with multi-column sorting
- **Charts**: Recharts — donut chart with center overlay text for asset allocation

### Backend
- **Entry point**: `app/main.py` — CORS allows `localhost:3000`
- **Directory layout**: `app/{api, core, db, models, schemas, services}`
- **Auth**: JWT access tokens (30min) + refresh token rotation; passlib/bcrypt; `get_current_user` dependency on all protected routes
- **KIS token lifecycle**: Redis caches the 24h KIS access token; proactive rotation before expiry
- **KIS rate limiting**: `kis_rate_limiter.py` token bucket (5/s, burst=20); all KIS HTTP call sites in `kis_price.py` and `price_snapshot.py` call `await acquire()` before the request; configurable via `KIS_RATE_LIMIT_PER_SEC`, `KIS_RATE_LIMIT_BURST`, `KIS_MOCK_MODE` settings
- **Price calculation**: Current prices and P&L computed dynamically via KIS API (`asyncio.gather`) — never stored in DB
- **Encryption**: AES-256 for storing KIS API credentials; master key from env

### Database (PostgreSQL via async SQLAlchemy)
Core tables: `users`, `portfolios`, `holdings`, `transactions`
Migrations managed with Alembic.

### Security patterns
- IDOR prevention: always validate `user_id` ownership before returning/modifying records
- KIS credentials stored AES-256 encrypted; master key in env, never in code
- Bearer token required on all non-auth endpoints

## Development Workflow

### Workflow Commands (recommended entry points)

For most work, start with a workflow command that chains the full pipeline automatically:

| Command | Purpose | User Gates |
|---------|---------|------------|
| `/sprint` | Full cycle: discover → implement → review → release → docs | 2 (priorities, deploy) |
| `/feature <desc>` | Feature pipeline: design → implement → review → release | 1 (PRD approval) |
| `/fix <desc>` | Bug fix pipeline: diagnose → fix → review → release | 0 (auto, stops on block) |
| `/quick` | Fast maintenance: discover-tasks → auto-task → docs | 0 (refuses sensitive work) |

### Individual Commands

For granular control, use individual commands:

| Command | Purpose |
|---------|---------|
| `/plan` | Create implementation plan via planner agent — waits for confirmation |
| `/tdd` | TDD workflow via tdd-guide agent — tests first |
| `/code-review` | Security + quality review via code-reviewer agent |
| `/python-review` | Python-specific review (ruff, mypy, bandit) |
| `/build-fix` | Incrementally fix build/type errors |
| `/auto-task` | Batch execute all tasks.md items |
| `/next-task` | Execute single next task |
| `/discover-tasks` | Refresh tasks.md and todo.md |
| `/update-docs` | Sync docs with codebase |
| `/fix-alerts` | Diagnose and fix price alert delivery issues |
| `/log-check` | Review recent error logs for anomalies |
| `/e2e-check` | Run Playwright E2E suite on critical flows |
| `/fix-ui` | Fix UI bug from screenshot or user report |
| `/visual-qa` | Run screenshot-based visual regression check |

### Team Commands (multi-agent analysis)

| Command | Purpose |
|---------|---------|
| `/team-discover` | 5 analysts → prioritized tasks and roadmap |
| `/team-feature` | 4 designers → PRD and task list |
| `/team-review` | 4 reviewers → unified code review verdict |
| `/team-release` | 4 validators → go/no-go release decision |
| `/team-debug` | 4 analysts → root cause diagnosis |
| `/team-implement` | 3 workers (backend/frontend/infra) → parallel task execution |

## Agents (`.claude/agents/`)

| Agent | Model | When to Use |
|-------|-------|-------------|
| `planner` | opus | New features, complex refactoring |
| `architect` | opus | Architectural decisions |
| `tdd-guide` | sonnet | Any new code — enforce tests-first |
| `code-reviewer` | sonnet | After every code change |
| `security-reviewer` | sonnet | Auth, API endpoints, KIS credential handling |
| `database-reviewer` | sonnet | Schema changes, SQL queries, Alembic migrations |
| `migration-reviewer` | sonnet | Alembic migration safety and reversibility |
| `perf-analyzer` | sonnet | Bundle size, query performance, caching |
| `doc-updater` | sonnet | Keep docs in sync with codebase changes |
| `e2e-runner` | sonnet | Playwright E2E tests for critical user flows |
| `visual-qa` | sonnet | Screenshot-based UI regression checks |

## Hooks (`.claude/hooks/`)

Automatically run on tool use — configured in `.claude/settings.json`:

| Hook | Trigger | Action |
|------|---------|--------|
| `pre-bash-block-no-verify.sh` | Bash `--no-verify` | Block git hook bypass |
| `pre-bash-git-push-reminder.sh` | `git push` | Checklist reminder |
| `post-edit-ts-check.sh` | Edit/Write `.ts`/`.tsx` | `tsc --noEmit` in `frontend/` |
| `post-edit-py-format.sh` | Edit/Write `.py` | `ruff check` + `print()` warning |
| `post-edit-console-warn.sh` | Edit/Write `.ts`/`.tsx`/`.js` | Warn on `console.log` |

## Rules (`.claude/rules/`)

Rules apply by file path pattern. Key rules to follow:

**Common (all files):**
- Immutability: create new objects, never mutate in-place
- File size: 200–400 lines typical, 800 max; extract when larger
- Functions: < 50 lines; nesting depth ≤ 4 levels
- TDD mandatory: write tests before implementation; 80%+ coverage required
- No hardcoded secrets — always `process.env` / `os.environ`

**TypeScript (`frontend/**`):**
- Explicit types on all exported functions and component props
- Use `interface` for object shapes, `type` for unions/utilities
- Avoid `any` — use `unknown` + narrowing
- Zod for schema validation and type inference
- No `console.log` in production code

**Python (`backend/**`):**
- PEP 8 + type annotations on all function signatures
- Immutable dataclasses (`@dataclass(frozen=True)`) where appropriate
- `black` for formatting, `ruff` for linting, `mypy` for types
- `pytest` for tests with `@pytest.mark.unit` / `.integration` markers
- Use `logging` module — no `print()` statements

## Git Conventions

```
<type>: <description>   # keep under 70 characters

Types: feat, fix, refactor, docs, test, chore, perf, ci
```

## Environment

Copy `backend/.env.example` to `backend/.env` before running the backend.
