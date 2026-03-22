# Feature Batch Review -- 2026-03-23

## Summary

Review of features implemented between 2026-03-21 and 2026-03-23, based on git log analysis and codebase scan. This batch includes: notification center, trade memo, Sentry APM, MetricsMiddleware, KIS transaction history, and portfolio reorder.

## Features Reviewed

### 1. In-app Notification Center (backend + frontend)
- `notifications` table (user_id, type, title, body, is_read)
- API: `GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all`
- Alert SSE integration: triggered alerts create notification records
- Frontend: `NotificationBell.tsx` with unread badge, dropdown panel, `useNotifications.ts` TanStack Query hook

### 2. Trade Memo / Investment Journal
- `transactions.memo` column (String(500), nullable)
- `PATCH /portfolios/{id}/transactions/{tid}` for memo update
- Frontend inline edit UI with optimistic update

### 3. Sentry APM Integration
- Backend: `sentry-sdk[fastapi]` with `SENTRY_DSN` env var
- Frontend: `@sentry/nextjs` via `SentryInit.tsx` component (production only)
- Error Boundary `captureException` integration

### 4. MetricsMiddleware
- `app/middleware/metrics.py` -- `X-Process-Time` response header
- structlog `process_time_ms` field for all requests

### 5. KIS Transaction History
- `kis_transaction.py` service: domestic (TTTC8001R) + overseas (TTTS3035R)
- `GET /portfolios/{id}/kis-transactions` endpoint with date range params

### 6. Portfolio Reorder
- `portfolios.display_order` column
- `PATCH /portfolios/reorder` endpoint
- Frontend: `@dnd-kit/core` + `@dnd-kit/sortable` drag-and-drop

## Strengths

- Notification system is well-structured: separate table, TanStack Query optimistic updates, unread-first ordering with limit
- MetricsMiddleware provides operational visibility without external dependencies
- Sentry integration is conditional (production only) and covers both frontend and backend
- Trade memo is lightweight (single column) with inline editing UX
- Portfolio reorder uses a dedicated `display_order` column rather than fragile position-based logic

## Issues Found

### Critical
- None identified.

### Medium
- `kis_transaction.py` has 0% test coverage (70 statements). This is the only service module with no tests. Should be prioritized.
- Overall backend test coverage dropped from 92% to 87%, primarily due to `kis_transaction.py` and codebase growth.

### Low / Suggestions
- `NotificationBell.tsx` uses raw DOM event handling (`useRef` + manual click-outside detection). Consider using Radix UI `Popover` from shadcn/ui for better accessibility.
- The `notifications` API currently has no pagination beyond `LIMIT 100`. For users with many alerts triggering, consider cursor-based pagination.
- `SentryInit.tsx` initializes Sentry inside a `useEffect` in a client component. Consider using the standard `@sentry/nextjs` `instrumentation.ts` hook for server-side coverage.

## Verdict

All features are well-implemented and functional. The primary action item is adding tests for `kis_transaction.py` to restore coverage above 90%. The notification center and trade memo complete two items from the P1/P2 roadmap. Build passes cleanly with 0 lint errors.
