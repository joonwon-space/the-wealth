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
- [x] Fix N+1 query in list_portfolios — single query with LEFT JOIN + GROUP BY
- [x] Add DB indexes: holdings, transactions, sync_logs

## Frontend Error Handling
- [x] Settings page — try-catch + toast on handleSaveLabel, handleDeleteAccount
- [x] Settings page — .catch() on initial portfolio/sync-log fetch
- [x] Settings page — success toast on KIS account add/edit/delete

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
