# Trading Feature Architecture

주문 lifecycle, Redis 락, settlement 스케줄러, reconciliation 흐름.

---

## 1. 주문 상태 전이도

```
                 ┌─────────────────────────┐
                 │   사용자가 주문 요청        │
                 └──────────┬──────────────┘
                            │
                            ▼
                       ┌─────────┐
                       │ pending │  ← KIS에 주문 전송 성공, 체결 미확인
                       └────┬────┘
                            │ 5분 간격 settlement 체크
                    ┌───────┴───────┐
                    │               │
                    ▼               ▼
               ┌─────────┐    ┌──────────┐
               │ partial │    │  filled  │  ← 완전 체결
               └────┬────┘    └──────────┘
                    │ (추가 체결)
                    ▼
               ┌──────────┐
               │  filled  │
               └──────────┘

          또는 사용자가 취소:
               ┌───────────┐
               │ cancelled │  ← /orders/{id}/cancel 호출
               └───────────┘

          KIS 에러 시:
               ┌────────┐
               │ failed │  ← KIS API 오류 응답
               └────────┘
```

**`Order.status` 값** (`backend/app/models/order.py:34-35`):
```python
status: Mapped[str] = mapped_column(
    String(20), nullable=False, default="pending", index=True
)  # pending | filled | partial | cancelled | failed
```

---

## 2. Redis 락 구조

주문 실행 시 두 종류의 Redis 제어 사용 (`kis_order_place.py`):

### 2.1 중복 주문 방지 락

```python
_ORDER_LOCK_PREFIX = "order_lock:{portfolio_id}:{ticker}"
_ORDER_LOCK_TTL = 10  # seconds
```

동작 (`kis_order_place.py:123-129`):
```python
async def _acquire_order_lock(portfolio_id: int, ticker: str) -> bool:
    key = _ORDER_LOCK_PREFIX.format(portfolio_id=portfolio_id, ticker=ticker)
    # SET NX EX 10 — 이미 락이 있으면 False 반환
    await _cache.setex(key, _ORDER_LOCK_TTL, "1")
```

국내 주문 (`line 220`)과 해외 주문 (`line 321`) 모두 락 획득 실패 시 즉시 거부.
TTL 10초로 자동 해제 — 무기한 lock-out 방지.

### 2.2 주문 빈도 제한

```python
_RATE_LIMIT_PREFIX = "order_rate:{user_id}"
_RATE_LIMIT_TTL = 60  # seconds
_RATE_LIMIT_MAX = 5   # 5회/분
```

1분 슬라이딩 윈도우 내 5회 초과 시 주문 거부.
(KIS API amplification 방지와 별개로 앱 레벨에서도 적용)

---

## 3. 주문 실행 흐름 (국내 예시)

```
POST /api/v1/orders/domestic
    │
    ▼
is_within_market_hours()          ← KST 09:00~15:30 확인
    │
    ▼
_check_rate_limit(user_id)        ← Redis order_rate:{user_id} 카운터
    │
    ▼
_acquire_order_lock(portfolio_id, ticker)   ← Redis order_lock:{portfolio_id}:{ticker}
    │
    ▼
_get_domestic_tr_id(order_type, account_type, is_paper_trading)
    │
    ▼
await acquire()                   ← KIS rate limiter (5/s, burst=20)
    │
    ▼
POST {KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash
    │
    ▼
if rt_cd != "0": raise ValueError
    │
    ▼
DB: INSERT orders (status="pending", order_no=KIS응답의 ODNO)
```

구현: `backend/app/services/kis_order_place.py:196-267`

---

## 4. Settlement — 미체결 주문 자동 처리

### 4.1 스케줄러 실행 주기

`backend/app/services/scheduler.py:488-498`:
```python
scheduler.add_job(
    _settle_pending_orders,
    trigger="cron",
    day_of_week="mon-fri",
    hour="9-15",
    minute="*/5",           # 9:00~15:59 5분 간격
    timezone="Asia/Seoul",
    id="settle_orders",
)
```

**실행 시간**: 평일 KST 09:05, 09:10, ..., 15:55 (5분 간격)

### 4.2 settle_pending_orders() 동작

`backend/app/services/order_settlement.py:74-174`:

```
DB에서 status IN ("pending", "partial") orders 조회
    │
    ▼
order_no 목록으로 check_filled_orders(KIS) 호출 → FilledOrderInfo 목록
    │
    ▼
for each order:
    if order_no in filled_map:
        new_filled = info.filled_quantity - prev_filled_quantity
        if is_fully_filled:
            order.status = "filled"    → counts["settled"] += 1
        else:
            order.status = "partial"   → counts["partial"] += 1
        _update_holdings_for_fill(order, new_filled, info.filled_price)
    else:
        counts["unchanged"] += 1
    │
    ▼
반환: {"settled": N, "partial": N, "unchanged": N}
```

### 4.3 체결 시 Holdings 업데이트

`_update_holdings_for_fill()` (`order_settlement.py:21-72`):
- 매수: `holding.quantity += new_filled`, 평균 단가 재계산
- 매도: `holding.quantity -= new_filled`
- `Transaction` 레코드 생성 (매수/매도 이력)

---

## 5. Reconciliation — KIS ↔ DB 불일치 해소

`backend/app/services/reconciliation.py`

### 목적
settlement가 누락되거나 외부에서 KIS 계좌 잔고가 변경된 경우 DB를 KIS 실제 잔고로 맞춤.

### 처리하는 불일치 유형

```python
async def reconcile_holdings(db, portfolio_id, kis_holdings):
    # KIS 보유 종목이 DB에 없으면 → INSERT
    # DB에 있지만 quantity가 다르면 → UPDATE quantity
    # KIS에 없는데 DB에 있으면 → 유지 (수동 추가 종목 보호)
```

### 호출 시점

`scheduler.py:120` — `_sync_all_accounts()` 내부:
```python
counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
```

실행 스케줄: KST 06:30 (미국 장 마감 후), 08:00 (국내 장 개시 전), 16:00 (국내 장 마감 직후) — `_preload_prices`와 `_sync_all_accounts`를 통해 간접 호출.

---

## 6. 전체 스케줄러 Job 표

`backend/app/services/scheduler.py:428-519` 기준:

| Job ID | 함수 | 실행 시각 (KST) | 목적 |
|--------|------|----------------|------|
| `kis_sync_us` | `_sync_all_accounts` | 평일 06:30 | 미국 장 마감 후 잔고 동기화 |
| `daily_close_snapshot` | `_snapshot_daily_close` | 평일 16:10 | 전일 종가 스냅샷 저장 |
| `preload_prices_am` | `_preload_prices` | 평일 08:00 | 장 개시 전 가격 캐시 워밍 |
| `preload_prices_pm` | `_preload_prices` | 평일 16:00 | 국내 장 마감 후 가격 캐시 워밍 |
| `fx_rate_snapshot` | `_save_fx_rate_snapshot` | 평일 16:30 | 환율 스냅샷 (USD/KRW 등) |
| `settle_orders` | `_settle_pending_orders` | 평일 09:05~15:55, 5분 간격 | 미체결 주문 자동 체결 확인 |
| `collect_benchmark` | `_collect_benchmark_snapshots` | 평일 16:20 | KOSPI200/S&P500 스냅샷 |

**실패 처리**: 각 job은 try/except로 감싸고 `_record_job_failure(job_id, exc)` 호출. job 실패가 서버 전체에 영향을 주지 않음.

---

## Related

- [`docs/architecture/kis-integration.md`](./kis-integration.md) — TR_ID, rate limiter, KIS API 에러 코드
- [`docs/architecture/database-schema.md`](./database-schema.md) — orders 테이블 스키마, indexes
- [`docs/architecture/feature-analytics.md`](./feature-analytics.md) — scheduler jobs 전체 표
