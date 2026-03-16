# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

Promoted from Milestone 10 UX/Performance items.

## Performance
- [x] Shorten KIS price cache TTL from 1h to 5min
- [x] Dashboard force-refresh — clears price cache + refresh button

## UX
- [ ] Add Cmd+K / Ctrl+K keyboard shortcut to open stock search from any dashboard page
- [ ] Add password change API (POST /auth/change-password) + revoke all refresh tokens
- [ ] Portfolio detail — add date input to transaction create form (traded_at field)
- [ ] HoldingsTable — add role="button" and onKeyDown to sortable column headers
