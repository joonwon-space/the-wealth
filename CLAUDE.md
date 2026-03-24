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
- `docs/plan/todo.md` — 6-milestone implementation roadmap

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

Follow this order for every feature:

1. **Plan** (`/plan`) — Use planner agent, wait for confirmation before coding
2. **TDD** (`/tdd`) — Write tests first (RED), implement (GREEN), refactor
3. **Review** (`/code-review` or `/python-review`) — Run after writing code
4. **Commit** — Follow conventional commit format (see below)

## Slash Commands (`.claude/commands/`)

| Command | Purpose |
|---------|---------|
| `/plan` | Create implementation plan via planner agent — waits for confirmation |
| `/tdd` | TDD workflow via tdd-guide agent — tests first |
| `/code-review` | Security + quality review via code-reviewer agent |
| `/python-review` | Python-specific review (ruff, mypy, bandit) |
| `/build-fix` | Incrementally fix build/type errors |

## Agents (`.claude/agents/`)

| Agent | Model | When to Use |
|-------|-------|-------------|
| `planner` | opus | New features, complex refactoring |
| `architect` | opus | Architectural decisions |
| `tdd-guide` | sonnet | Any new code — enforce tests-first |
| `code-reviewer` | sonnet | After every code change |
| `security-reviewer` | sonnet | Auth, API endpoints, KIS credential handling |
| `database-reviewer` | sonnet | Schema changes, SQL queries, Alembic migrations |

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
