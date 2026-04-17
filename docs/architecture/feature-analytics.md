# Analytics Feature Architecture

성과 지표 계산식, 데이터 소스, 스케줄러 job 표.

---

## 1. 성과 지표 계산식

구현: `backend/app/api/analytics_metrics.py`

### 1.1 Total Return Rate

```
total_return_rate = (total_current - total_invested) / total_invested × 100
```

- `total_invested`: 모든 holding의 `avg_price × quantity` 합산 (`_compute_holding_pnl()`, `analytics_metrics.py:121-131`)
- `total_current`: 현재 가격 × quantity 합산 (KIS API 조회 또는 Redis 캐시)

### 1.2 MDD (Maximum Drawdown)

```python
def _calc_mdd(values: list[float]) -> float:
    # analytics_metrics.py:43-55
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100  # %
```

입력: `price_snapshots` 기반 일별 포트폴리오 가치 시계열 (최근 1년).

### 1.3 CAGR (Compound Annual Growth Rate)

```python
def _calc_cagr(start: float, end: float, years: float) -> Optional[float]:
    # analytics_metrics.py:58-62
    if start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100  # %
```

- `start`: 첫 번째 price_snapshot 날짜의 포트폴리오 가치
- `end`: 현재 포트폴리오 가치
- `years`: 기간 (일수 / 365)

### 1.4 Sharpe Ratio

```python
_RISK_FREE_RATE = 0.035  # 연 3.5% (국고채 기준, analytics_metrics.py:40)

def _calc_sharpe(daily_returns: list[float]) -> Optional[float]:
    # analytics_metrics.py:65-77
    if len(daily_returns) < 5:
        return None
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / n
    std = variance ** 0.5
    annual_return = mean * 252          # 연환산 (252 거래일)
    annual_std = std * (252 ** 0.5)
    return (annual_return - _RISK_FREE_RATE) / annual_std
```

`daily_returns`: price_snapshots의 연속된 날짜 간 포트폴리오 가치 변화율 목록.

### 1.5 Monthly Returns

`GET /api/v1/analytics/monthly-returns` (`analytics_metrics.py:244`):
- `price_snapshots` 에서 각 월의 마지막 거래일 종가를 취합
- 월간 수익률 = (이번 달 마지막 일 가치 - 지난 달 마지막 일 가치) / 지난 달 가치 × 100
- 기본 cutoff: `today - 365일` (최근 1년) — optional `?since=` 파라미터로 변경 가능

---

## 2. 데이터 소스

### price_snapshots 테이블

일별 종가 스냅샷. `_snapshot_daily_close()` 스케줄러가 평일 16:10에 저장.

```sql
-- 기본 구조 (analytics에서 사용하는 컬럼)
SELECT snapshot_date, ticker, close_price
FROM price_snapshots
WHERE portfolio_id = :pid
  AND snapshot_date >= :cutoff   -- PERF-101: 1년 컷오프 추가
ORDER BY snapshot_date ASC
```

### fx_rate_snapshots 테이블

환율 스냅샷 (USD/KRW 등). `_save_fx_rate_snapshot()` 스케줄러가 평일 16:30에 저장.
해외 종목의 KRW 환산 가치 계산 시 사용.

### index_snapshots 테이블

벤치마크 지수 스냅샷 (KOSPI200, S&P500). `_collect_benchmark_snapshots()` 스케줄러가 평일 16:20에 저장.

### Redis 캐시

현재 가격: `_get_cached_price(ticker)` 사용. 캐시 미스 시 KIS API 직접 조회.
분석 결과 캐시: `analytics:{user_id}:{endpoint}` 키로 Redis에 저장 (TTL: 5분).

---

## 3. 스케줄러 Job 표

`backend/app/services/scheduler.py:428-519` 기준:

| Job ID | 함수 | 실행 시각 (KST) | 목적 | 실패 동작 |
|--------|------|----------------|------|----------|
| `kis_sync_us` | `_sync_all_accounts` | 평일 06:30 | 미국 장 마감 후 잔고 동기화 | 로그 + `_record_job_failure` |
| `daily_close_snapshot` | `_snapshot_daily_close` | 평일 16:10 | 전일 종가 price_snapshots 저장 | 로그 + `_record_job_failure` |
| `preload_prices_am` | `_preload_prices` | 평일 08:00 | 장 개시 전 가격 캐시 워밍 + 잔고 동기화 | 로그 + `_record_job_failure` |
| `preload_prices_pm` | `_preload_prices` | 평일 16:00 | 국내 장 마감 후 가격 캐시 워밍 + 잔고 동기화 | 로그 + `_record_job_failure` |
| `fx_rate_snapshot` | `_save_fx_rate_snapshot` | 평일 16:30 | 환율 스냅샷 저장 | 로그 + `_record_job_failure` |
| `settle_orders` | `_settle_pending_orders` | 평일 09:05~15:55, 5분 간격 | 미체결 주문 자동 체결 확인 | 로그 + `_record_job_failure` |
| `collect_benchmark` | `_collect_benchmark_snapshots` | 평일 16:20 | KOSPI200/S&P500 스냅샷 | 로그 + `_record_job_failure` |

**실패 처리 공통 패턴** (`scheduler.py:424-425`):
```python
except Exception as exc:
    _record_job_failure(job_id, exc)   # 실패 카운터 증가, 로그 출력
    # 서버 전체 영향 없음 — 다음 실행 주기에 재시도
```

---

## 4. 벤치마크 데이터 수집 흐름

구현: `backend/app/services/kis_benchmark.py`

```
_collect_benchmark_snapshots() [평일 16:20]
    │
    ▼
KIS 계정 조회 (첫 번째 활성 계정 사용)
    │
    ▼
asyncio.gather(
    _fetch_domestic_index(app_key, app_secret, "KOSPI200", "FHKUP03500100"),
    _fetch_overseas_index(app_key, app_secret, "SP500", "FHKST03030100"),
)
    │
    ▼
index_snapshots 테이블에 INSERT (upsert)
    │
    ▼
로그: "Saved benchmark snapshots: KOSPI200=XXXX.XX SP500=XXXX.XX"
```

TR_ID:
- KOSPI200: `FHKUP03500100` (국내지수 현재가, `kis_benchmark.py:7`)
- S&P500: `FHKST03030100` (`kis_benchmark.py:36`)
- KOSPI200 시장코드: `"0003"` (`kis_benchmark.py:70`)

---

## 5. 분석 캐시 구조

```python
# analytics_utils.py:13-14
def analytics_key(user_id: int, endpoint: str) -> str:
    return f"analytics:{user_id}:{endpoint}"

# 예시 키
"analytics:42:metrics"
"analytics:42:monthly-returns:2025-04-17"
"analytics:42:sector-allocation"
"analytics:42:fx-gain-loss"
```

캐시 무효화 시점:
- 포트폴리오 자산 변경 시 (`invalidate_analytics_cache(user_id)`)
- 직접 delete: `redis-cli del "analytics:42:metrics"` (디버깅용)

---

## Related

- [`docs/architecture/feature-trading.md`](./feature-trading.md) — 스케줄러 job 상세, settlement 흐름
- [`docs/architecture/database-schema.md`](./database-schema.md) — price_snapshots, fx_rate_snapshots, index_snapshots 스키마
- [`docs/architecture/kis-integration.md`](./kis-integration.md) — 벤치마크 TR_ID, rate limiter
