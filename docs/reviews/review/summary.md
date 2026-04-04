# Code Review Summary — Sprint 8 (2026-04-04)

## Verdict: REQUEST CHANGES

3 reviewers returned request-changes (correctness, performance, maintainability). Security approved with 2 low-severity findings. No blockers found. All issues are medium or lower severity — none block safety, auth, or financial accuracy. The changes are safe to ship after addressing the high-priority performance issue (PERF-001).

---

## Must Fix (before merge)

| # | ID | Title | Severity | Reviewer | Location | Fix |
|---|-----|-------|----------|----------|----------|-----|
| 1 | PERF-001 | Sequential get_cached_price calls in fx-gain-loss | high | performance | `analytics_fx.py:113-116` | Use `asyncio.gather(*[_get_cached_price(h.ticker) for h in overseas])` |

---

## Should Fix (before or soon after merge)

| # | ID | Title | Severity | Reviewer | Location | Fix |
|---|-----|-------|----------|----------|----------|-----|
| 1 | COR-002 | invalidate_analytics_cache misses portfolio-specific cache keys | medium | correctness | `analytics_utils.py:33-41` | Use Redis pattern scan or document TTL-based expiry as accepted behavior |
| 2 | PERF-002 | Sequential cache reads in get_metrics exception fallback | medium | performance | `analytics_metrics.py:150-153` | Use `asyncio.gather` in fallback exception handler |
| 3 | MAIN-001 | Duplicated date_ticker_map construction across analytics modules | medium | maintainability | `analytics_metrics.py:182`, `analytics_history.py:92` | Extract `build_date_ticker_map()` to `analytics_utils.py` |
| 4 | SEC-002 | currency_pair input has no allowlist validation | low | security | `analytics_fx.py:158` | Add `valid_pairs = {'USDKRW'}` allowlist check |

---

## Consider (optional improvements)

| # | ID | Title | Severity | Reviewer | Location | Fix |
|---|-----|-------|----------|----------|----------|-----|
| 1 | COR-001 | _nearest_fx_rate candidate selection confusingly labeled | medium | correctness | `analytics_fx.py:96-110` | Rename intermediate vars for clarity; logic is correct but opaque |
| 2 | COR-003 | Sharpe ratio uses population variance instead of sample variance | low | correctness | `analytics_metrics.py:69-77` | Use `/ (n-1)` for financial convention |
| 3 | MAIN-003 | analytics.py shim lacks docstring explaining its role | low | maintainability | `analytics.py:1` | Add module docstring clarifying this is a backward-compat shim |
| 4 | MAIN-004 | Three analytics routers repeat the same prefix | low | maintainability | `analytics_metrics.py:37` etc. | Add grouping comment in `main.py` |
| 5 | SEC-001 | Importing private _get_cached_price function | low | security | `analytics_fx.py:25` | Expose as public function |

---

## Review Statistics

- Correctness:     request-changes — 4 findings
- Security:        approve — 2 findings
- Performance:     request-changes — 3 findings (1 informational)
- Maintainability: request-changes — 4 findings
- Total unique findings: 10 (after dedup — COR-004 merged into COR-002)

Generated: 2026-04-04
