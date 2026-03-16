# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Transaction History (from Milestone 9)
- [ ] Transaction list API — GET /portfolios/{id}/transactions with date filter
- [ ] Transaction create API — POST /portfolios/{id}/transactions (buy/sell)
- [ ] Transaction list UI — table with date, type, ticker, quantity, price columns
- [ ] Transaction create form — modal with buy/sell toggle, stock search, quantity, price

## Search UX (from Milestone 9)
- [ ] Save recent search queries to localStorage (last 5) and show as suggestions
- [ ] Add overseas stock market label (NYSE/NASDAQ/AMEX) to search results display

## Dashboard Improvement
- [ ] Dashboard summary should aggregate across all KIS-linked portfolios (not just user-level credentials)
- [ ] Portfolio detail page — show current price and P&L per holding (use KIS price API via linked account)
