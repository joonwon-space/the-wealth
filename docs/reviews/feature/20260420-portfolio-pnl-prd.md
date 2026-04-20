# PRD: 포트폴리오별 수익률/손익 표시

**Feature:** Portfolio P&L Summary on List Screen
**Date:** 2026-04-20
**Status:** Draft — Pending User Approval

---

## 1. Background & Goal

The portfolio list page (`/dashboard/portfolios`) currently shows only `holdings_count` and `total_invested` (investment principal) for each portfolio. Users cannot tell at a glance how their portfolios are performing without clicking into each one individually.

**Goal:** Display real-time evaluation value (market value), P&L amount, and return rate directly on the portfolio list rows, enabling at-a-glance performance monitoring.

---

## 2. User Stories

- As a user, I want to see the current market value of each portfolio on the list screen so I can assess my wealth without navigating away.
- As a user, I want to see the P&L amount (+/- in KRW) and return rate (%) for each portfolio so I can compare performance across accounts.
- As a user with no KIS account connected, I want to see a graceful "—" placeholder so the screen does not break.
- As a user with USD portfolios, I want to see values converted to KRW for consistent comparison.

---

## 3. Scope (MVP)

### In scope
- New backend endpoint `GET /portfolios/with-prices` that returns per-portfolio aggregated P&L in KRW
- Frontend `SortablePortfolioRow` extended to show `market_value_krw`, `pnl_amount`, `pnl_rate`
- KIS not connected → all three fields return `null`, rendered as "—"
- USD holdings → FX-converted to KRW before summing
- De-duplicated ticker fetching across all portfolios (fetch each unique ticker once)
- Redis price cache reuse; no extra KIS calls if prices are already cached
- Korean color convention: red (`text-korean-up`) for positive P&L, blue (`text-korean-down`) for negative

### Out of scope
- Real-time SSE push to the portfolio list (separate feature)
- Per-holding P&L breakdown (already exists at detail screen)
- Target value tracking / progress bar (separate feature)

---

## 4. Technical Design

### 4.1 Backend — New Endpoint

**`GET /portfolios/with-prices`** (added to `backend/app/api/portfolios.py`)

Response schema (extends `PortfolioResponse`):

```python
class PortfolioWithPricesResponse(PortfolioResponse):
    market_value_krw: Optional[Decimal] = None   # sum of all holdings market values in KRW
    pnl_amount: Optional[Decimal] = None          # market_value_krw - total_invested_krw
    pnl_rate: Optional[Decimal] = None            # pnl_amount / total_invested_krw * 100
    prices_available: bool = False                 # False when KIS not connected
```

**Algorithm:**
1. Load all portfolios + holdings for user in 2 queries (portfolio list + all holdings via `portfolio_id IN (...)`)
2. Collect all unique domestic tickers and unique overseas tickers across all portfolios
3. Look up the user's first KIS account (same fallback logic as `portfolio_holdings.py`)
4. Fetch all unique prices in parallel via `asyncio.gather` (reuses `get_or_fetch_domestic_price` / `get_or_fetch_overseas_price`)
5. Fetch USD/KRW FX rate once if any overseas holdings exist
6. Aggregate per portfolio: sum `quantity * current_price` (FX-adjusted to KRW)
7. If no KIS account or fetch fails, return `market_value_krw=null`, `prices_available=False`

**Rate limit:** Same `30/minute` as other KIS-calling endpoints.

**Sensitive path note:** This endpoint does NOT touch `security.py`, `auth*`, or `transaction*`. It reuses existing KIS price utilities.

### 4.2 Backend — Schema

Add `PortfolioWithPricesResponse` to `backend/app/schemas/portfolio.py`.

### 4.3 Backend — Tests

- `backend/tests/api/test_portfolios_with_prices.py`
- Unit tests: aggregation logic with mocked KIS prices
- Integration test: endpoint returns 200, correct P&L when prices available; returns null fields when no KIS account

### 4.4 Frontend — Type Update

Extend `Portfolio` interface in `page.tsx`:

```typescript
interface Portfolio {
  // ... existing fields ...
  market_value_krw: string | null;
  pnl_amount: string | null;
  pnl_rate: string | null;
  prices_available: boolean;
}
```

### 4.5 Frontend — fetchPortfolios

Change `api.get("/portfolios")` to `api.get("/portfolios/with-prices")`.

### 4.6 Frontend — SortablePortfolioRow Stats Section

Replace the current stats block (lines 167–170):

```
holdings_count개 종목
₩total_invested
```

With a two-column layout:

```
holdings_count개 종목    [market_value_krw or —]
₩total_invested         [+pnl_amount (pnl_rate%)]
```

- `market_value_krw`: formatted with `formatKRW`, shown when not null
- `pnl_amount` + `pnl_rate`: formatted with `formatPnL` and `formatRate`; colored red (positive) or blue (negative) per Korean convention
- When `prices_available === false` or values are null: show "—" with `text-muted-foreground`
- Loading skeleton updated to cover the wider stats area

### 4.7 Frontend — Tests

- `frontend/src/app/dashboard/portfolios/__tests__/page.test.tsx`
- Test positive P&L renders red color class
- Test negative P&L renders blue color class
- Test null prices renders "—"
- Test `formatKRW`, `formatPnL`, `formatRate` used correctly

---

## 5. Task Breakdown

### Task 1 — Backend: Schema addition
Add `PortfolioWithPricesResponse` to `backend/app/schemas/portfolio.py`.
- Complexity: S
- File: `backend/app/schemas/portfolio.py`

### Task 2 — Backend: Endpoint implementation
Add `GET /portfolios/with-prices` to `backend/app/api/portfolios.py`.
- Complexity: M
- Files: `backend/app/api/portfolios.py`
- Depends on: Task 1

### Task 3 — Backend: Tests
Write unit + integration tests for the new endpoint.
- Complexity: M
- Files: `backend/tests/api/test_portfolios_with_prices.py`
- Depends on: Task 2

### Task 4 — Frontend: Type + API update
Extend `Portfolio` interface and change fetch URL to `/portfolios/with-prices`.
- Complexity: S
- File: `frontend/src/app/dashboard/portfolios/page.tsx`

### Task 5 — Frontend: UI — stats row
Extend `SortablePortfolioRow` stats section to display market value, P&L amount, and return rate with Korean color convention.
- Complexity: M
- File: `frontend/src/app/dashboard/portfolios/page.tsx`
- Depends on: Task 4

### Task 6 — Frontend: Tests
Write component tests for the new stats display.
- Complexity: S
- Files: `frontend/src/app/dashboard/portfolios/__tests__/page.test.tsx`
- Depends on: Task 5

---

## 6. Complexity Estimate

**Overall: M (Medium)**

- Backend work is straightforward — logic already exists in `portfolio_holdings.py`, just needs to be lifted and aggregated
- Frontend is minimal UI extension — reuses existing `formatKRW`, `formatPnL`, `formatRate` utilities
- Main risk: cold Redis cache on first load triggers KIS API calls proportional to unique ticker count across all portfolios; mitigated by existing rate limiter and per-ticker Redis caching

---

## 7. Trade-offs & Design Decisions

| Decision | Rationale |
|----------|-----------|
| New endpoint `/with-prices` vs extending existing `/` | Keeps existing endpoint stable (no breaking change); clients that don't need prices continue using `/portfolios` |
| Aggregate in backend vs fetch per-portfolio from frontend | Single backend request; de-duplicated ticker fetches; avoids N×M frontend API calls |
| Return `null` for all P&L fields when KIS not connected | Consistent with existing holdings detail screen behavior |
| Convert all to KRW for list display | Users can compare portfolios on a single scale; USD detail is available on the holdings screen |
| No SSE push for list screen | Scope creep; portfolio list is not a trading screen; 30 s/5 min cache is acceptable |

---

## 8. Acceptance Criteria

- [ ] Portfolio list shows `market_value_krw`, `pnl_amount (%)` for each portfolio when KIS is connected
- [ ] Positive P&L is rendered in red; negative P&L is rendered in blue
- [ ] KIS not connected → all P&L fields show "—" without errors
- [ ] USD portfolio holdings are converted to KRW before displaying
- [ ] Backend tests pass with ≥80% coverage on new code
- [ ] No regression on existing `/portfolios` endpoint or holdings detail screen
- [ ] CI (backend + frontend) passes green
