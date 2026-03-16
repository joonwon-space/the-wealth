# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Backend Validation
- [x] Add PortfolioCreate.name min_length=1, max_length=100 validation
- [x] Add HoldingCreate quantity/avg_price gt=0 validation
- [x] Change TransactionCreate.type to Literal["BUY", "SELL"] + quantity/price gt=0
- [x] Add pagination params (offset/limit) to GET transactions endpoint
- [x] Add pagination params to GET /sync/logs endpoint

## Backend Performance
- [ ] Fix N+1 query in list_portfolios — replace per-portfolio stats query with single GROUP BY JOIN
- [ ] Add DB indexes: holdings(ticker, portfolio_id), transactions(portfolio_id, traded_at), sync_logs(user_id, synced_at)

## Frontend Error Handling
- [ ] Settings page — add try-catch to handleSaveLabel and handleDeleteAccount with toast feedback
- [ ] Settings page — add .catch() to initial portfolio/sync-log fetch with error state
- [ ] Settings page — show success toast after KIS account add/edit/delete

## Frontend UX
- [ ] Portfolio detail — replace browser confirm() for portfolio delete with shadcn Dialog
- [ ] Portfolio detail — add confirmation dialog before transaction delete
- [ ] Portfolio detail — pre-populate holding edit form with current quantity/avg_price values
- [ ] Portfolio detail — add quantity/price > 0 client-side validation on holding and transaction forms
- [ ] TransactionChart — change legend labels from English to Korean (매수/매도)
- [ ] Settings page — fix KIS account add form grid to grid-cols-1 sm:grid-cols-2 for mobile

## Frontend Tests
- [ ] Add PnLBadge component test (positive=red, negative=blue, zero=default)
- [ ] Add TransactionChart component test (monthly aggregation logic)
- [ ] Add StockSearchDialog test (recent search, chosung)

## Backend Tests
- [ ] Add KIS account CRUD API tests (add, list, update label, delete, duplicate check)
- [ ] Add portfolio rename API test
