# Codebase Review -- 2026-03-19

## Summary

Full codebase review following the completion of multiple improvement items identified in the 2026-03-18 review. This review assesses the current state after SSE hardening, test coverage expansion, middleware migration, dashboard fixes, and CI/CD additions.

## Strengths

- **Test coverage at 94%** (517 tests, 0 ruff lint errors). Router coverage significantly improved: dashboard.py 97%, prices.py 83%. All services at 93-100%.
- **SSE connection management is production-hardened**: per-user connection limit (3), 15-second heartbeat, idle detection, 2-hour max duration, graceful shutdown signaling.
- **Next.js proxy migration completed**: `middleware.ts` replaced with proxy convention, resolving the Next.js 16 deprecation warning. Duplicate middleware file conflict also resolved.
- **Overseas holdings display fixed**: USD prices now display correctly for foreign holdings; NaN values in dashboard totals eliminated.
- **Standardized error responses**: All exceptions flow through a unified envelope (`error.code`, `error.message`, `request_id`) via custom exception handlers in `main.py`.
- **CI/CD mature**: 7 GitHub Actions workflows (backend lint/test, frontend lint/typecheck/test/build, deploy, Docker build, CodeQL, E2E, Dependabot auto-merge). Self-hosted runner for deployment.
- **API versioning in place**: All routes under `/api/v1` prefix. Health check available at both `/health` and `/api/v1/health`.
- **Graceful shutdown**: SSE streams receive close signal, APScheduler stops cleanly via lifespan context manager.

## Issues Found

### Critical

- None identified.

### Medium

- **No automated DB backup**: PostgreSQL data on single self-hosted server without automated pg_dump or external storage. A disk failure would result in total data loss.
- **No monitoring/APM**: Service runs with structlog only. No alerting on errors, no response time tracking, no uptime monitoring. Silent failures in scheduled jobs (sync, snapshots) could go unnoticed.
- **Alert notification dispatch missing**: `alerts` CRUD is complete but no mechanism to actually notify users when price conditions are met. The scheduler and SSE streams do not check alert thresholds.

### Low / Suggestions

- **TanStack Query adoption**: Frontend still uses manual Axios state management. TanStack Query would provide caching, background refetch, and loading/error state management with less boilerplate.
- **Frontend test coverage**: Backend is at 94% but frontend unit test coverage is minimal (a few component tests). Adding tests for hooks (`usePriceStream`) and key pages would improve reliability.
- **Single uvicorn worker**: Production runs a single worker. CPU-bound operations (encryption, bulk P&L) could block the event loop under concurrent load. Consider `--workers 2` with scheduler isolation.
- **Portfolio GET by ID missing**: `GET /portfolios/{id}` endpoint does not exist as a standalone route. The frontend fetches holdings directly. This is functional but unconventional for REST APIs.

## Resolved Since Last Review (2026-03-18)

The following items from the previous review are now resolved:

- [x] HttpOnly cookie authentication (XSS defense)
- [x] SSE connection hardening (per-user limit, heartbeat, timeout)
- [x] Per-endpoint rate limiting (login 5/min, register 3/min, dashboard 120/min, sync 5/min)
- [x] DB indexes on FK columns
- [x] Legacy user columns (migration path documented)
- [x] Soft delete for transactions
- [x] API versioning (/api/v1)
- [x] Standardized error responses
- [x] Error Boundary + fallback UI
- [x] Bundle optimization (dynamic imports for charts)
- [x] Graceful shutdown
- [x] Test coverage 94% (target was 70%)
- [x] Commitlint + Husky
- [x] Next.js middleware -> proxy migration

## Verdict

The project is in strong shape for a personal portfolio dashboard. Core functionality is complete and well-tested. The primary gaps are operational (monitoring, backups, alerting) rather than functional. The codebase is clean (0 lint errors), well-structured, and maintains high test coverage. Ready for continued production use with the caveat that operational resilience (backups, monitoring) should be prioritized next.
