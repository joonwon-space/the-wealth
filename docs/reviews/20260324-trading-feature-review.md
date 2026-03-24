# Trading Feature Review -- 2026-03-24

## Summary

Review of the KIS stock trading feature implemented in commit `3d5064e` (auto-task: Trading Feature Step 1-8) and subsequent bug fixes. This feature adds domestic and overseas stock buy/sell order execution, pending order management, and cash balance queries via the KIS OpenAPI.

## Scope

- **Backend**: `orders.py` API router, `order.py` model, `kis_order.py` service, `kis_balance.py` service, `order.py` schema
- **Frontend**: `OrderDialog.tsx`, `PendingOrdersPanel.tsx`, `useOrders.ts` hook
- **Database**: New `orders` table (11th table)

## Strengths

- Clean separation of concerns: KIS API calls in `kis_order.py`/`kis_balance.py`, API layer in `orders.py`, frontend state in `useOrders.ts`
- Account-type-aware TR_ID routing (regular/ISA/pension/IRP) avoids incorrect API calls
- Duplicate order prevention via Redis lock (`order_lock:{portfolio_id}:{ticker}`, TTL 10s)
- Per-user rate limiting (5 orders/min) prevents accidental rapid-fire ordering
- Cash balance endpoint combines domestic + overseas holdings into a single response, eliminating the need for separate `is_overseas` queries
- Overseas evaluation fallback: when `frcr_evlu_pfls_amt` is 0, falls back to `sum(quantity * avg_price)` to avoid showing zero balance
- Order dialog UX: limit/market toggle, quick ratio buttons (10/25/50/100%), two-step confirmation
- Pending orders panel auto-detects filled orders (disappeared from list) and shows toast notification
- Cash balance cached in Redis (30s TTL) to reduce KIS API calls during rapid UI interactions
- Exchange rate sourced from frankfurter.app ECB API after KIS TTTS3012R proved unreliable

## Issues Found

### Critical
- None identified.

### Medium
- `kis_order.py`, `kis_balance.py`, and `orders.py` router have no test coverage yet. These modules handle real money operations and should be prioritized for testing.
- `orders.py` imports `json` inside function bodies (lines 397, 456) rather than at module top level.
- `_update_holdings` mutates the `holding` ORM object in-place (quantity, avg_price) rather than creating a new record. Acceptable for ORM but diverges from the project's immutability coding style.

### Low / Suggestions
- The `orders` table `name` column (String(100)) is nullable, but ticker names are almost always available at order time. Consider making it non-nullable with a default of the ticker value.
- `PendingOrdersPanel` uses a 5-second polling interval for pending orders. During market hours this is reasonable, but could be paused during off-hours like the SSE price stream does.
- The `_DOMESTIC_TICKER_RE` pattern (`^[0-9A-Z]{6}$`) may not correctly classify all ETF tickers or future overseas ticker formats.

## Verdict

Well-structured trading feature that correctly integrates with the KIS OpenAPI for both domestic and overseas markets. The dual-step confirmation UI and server-side duplicate prevention provide reasonable safeguards for a real-money operation. Primary gap is the absence of test coverage for the trading modules, which should be addressed before the next major release.
