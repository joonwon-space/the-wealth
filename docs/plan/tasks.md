# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Transaction History (from Milestone 9)
- [x] Transaction list API — GET /portfolios/{id}/transactions (desc by date, limit 200)
- [x] Transaction create API — POST /portfolios/{id}/transactions (BUY/SELL validation)
- [x] Transaction list UI — table in portfolio detail page
- [x] Transaction create form — inline form with buy/sell, ticker, quantity, price

## Search UX (from Milestone 9)
- [ ] Save recent search queries to localStorage (last 5) and show as suggestions
- [ ] Add overseas stock market label (NYSE/NASDAQ/AMEX) to search results display

## Dashboard Improvement
- [ ] Dashboard summary should aggregate across all KIS-linked portfolios (not just user-level credentials)
- [ ] Portfolio detail page — show current price and P&L per holding (use KIS price API via linked account)
