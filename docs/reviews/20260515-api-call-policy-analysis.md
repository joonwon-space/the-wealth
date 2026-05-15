# API 호출 정책 심층 분석 및 최적화 계획

**작성일**: 2026-05-15
**범위**: 백엔드 KIS API 호출 흐름, 캐싱, rate limit, 프론트엔드 데이터 흐름 전반
**배경**: 화면 전환 시 KIS 현재가 API 중복 호출 + 9시 장 시작 시간대 응답 지연 체감

---

## 1. 현황 요약

### 핵심 문제

| # | 문제 | 영향도 | 근거 위치 |
|---|------|--------|----------|
| **P0** | `kis_balance.py` 가 rate limiter 를 **완전히 우회** — 9시 폭주 시 KIS 429 발생 위험 | Critical | `kis_balance.py:91-99, 200-208, 296-303` |
| **P0** | `/stocks/{ticker}/detail`, `/chart/daily` 가 rate limiter + 재시도 **모두 우회** — `await client.get()` 직접 호출 | Critical | `stocks.py:125,187,201`, `chart.py:105,213` |
| **P1** | 대시보드 `_fetch_prices` 가 **cache-first 가 아닌 cache-write-only 패턴** — 30s 폴링 + 페이지 전환마다 항상 KIS 직격 | High | `dashboard.py:139-148` |
| **P1** | `kis_call_slot()` (rate + concurrency) 가 `kis_price.py` 에서만 사용. 나머지 KIS 서비스는 legacy `acquire()` (rate-only) — **동시 in-flight 연결 무제한** | High | `kis_balance/dividend/order_query/transaction/benchmark.py` |
| **P2** | Backend single-flight (request coalescing) 부재 — 같은 ticker 를 동시에 100명이 요청하면 KIS 100번 호출 | Medium | 모든 `_fetch_prices` 진입점 |
| **P2** | Frontend Query Key 가 페이지마다 분리(`["dashboard"]` vs `["portfolios", id, "holdings"]`) — backend 캐시 공유에 의존하나 backend도 dashboard 는 캐시 무시 | Medium | `page.tsx:43`, `HoldingsSection.tsx:87` |
| **P3** | Next.js Link prefetch 미활용 — 네비게이션 직전 prefetch 없음 | Low | 전반 |

### 데이터 흐름 핵심 한 줄

> **백엔드는 `price:{ticker}` 단일 키로 캐시를 공유할 수 있지만, 대시보드 자체가 매번 fresh fetch → 캐시를 덮어쓰기만 함 → 다른 화면들이 캐시 hit 해도 30초마다 한 번씩 KIS 로 풀 라운드트립이 발생.**

---

## 2. 상세 분석

### 2.1 페이지별 API 호출 매핑

#### `/dashboard` (메인 대시보드) — `frontend/src/app/dashboard/page.tsx`

| API | 트리거 | refetchInterval | staleTime | 백엔드 → KIS |
|-----|--------|-----------------|-----------|--------------|
| `GET /dashboard/summary` | 마운트 + 폴링 | 30s (SSE 없을 때만) | 60s | `_fetch_prices` → `fetch_domestic_price_detail` (FHKST01010100) + `fetch_overseas_price_detail` (HHDFS00000300) + `fetch_usd_krw_rate` (frankfurter.dev) |
| `GET /dashboard/cash-summary` (신규) | 마운트 + 폴링 | 30s | 30s | TTTC8434R + TTTS3012R + CTRP6504R per KIS 계좌 |
| `GET /analytics/portfolio-history?period=1M` | 마운트 | none | 5min | DB only (price_snapshots) |
| `GET /analytics/sector-allocation` | 마운트 | none | 5min | 캐시 |
| `GET /analytics/benchmark-delta?period=1M` | 마운트 | none | 5min | DB + 1회 KIS |
| `GET /dividends/upcoming` | 마운트 | none | 10min | DB |
| `GET /tasks/today` | 마운트 | none | 5min | DB |
| `SSE /prices/stream` | 마운트 (장중) | 30s push | — | 30초마다 보유종목 N개 → KIS N콜 |

**근거**: `page.tsx:257-303`

#### `/dashboard/portfolios/[id]` (포트폴리오 상세)

| API | 트리거 | staleTime | 백엔드 → KIS |
|-----|--------|-----------|--------------|
| `GET /portfolios` (전체) | 마운트 | 60s | DB only |
| `GET /portfolios/{id}/holdings/with-prices` | 마운트 | 기본(30s) | `get_or_fetch_domestic_price` (**cache-first**) + `get_or_fetch_overseas_price` (cache-first) + `fetch_usd_krw_rate` |
| `GET /portfolios/{id}/cash-balance` | 마운트 + 30s 폴링 | 15s | TTTC8434R + TTTS3012R + CTRP6504R |
| `GET /portfolios/{id}/rebalance-suggestion` | 마운트 | 5min | DB |
| `GET /analytics/portfolio-history?period=1M&portfolio_id=...` | 마운트 | 5min | DB |
| `GET /analytics/benchmark-delta?period=1M` | 마운트 | 5min | **dashboard 와 중복 가능 (key 동일)** |
| `GET /analytics/fx-gain-loss` | 마운트 | 10min | DB + 1회 KIS |
| `GET /portfolios/{id}/orders/pending` (KIS 연결시) | 마운트 + 30s 폴링 | 15s | KIS pending 조회 |

**근거**: `portfolios/[id]/page.tsx:62-103`, `HoldingsSection.tsx:84-89`, `AnalysisSection.tsx:39-67`

#### `/dashboard/stocks/[ticker]` (종목 상세)

| API | 트리거 | staleTime | 백엔드 → KIS |
|-----|--------|-----------|--------------|
| `GET /stocks/{ticker}/detail` | 마운트 (`useEffect`) | **캐시 없음** (axios + setState) | **rate-limit 우회** FHKST01010100 OR HHDFS00000300 + HHDFS76200200 + frankfurter.dev |
| `GET /chart/daily` | 마운트 + 기간 변경 | useTransition | **rate-limit 우회** FHKST03010100 OR HHDFS76240000 |

**근거**: `stocks/[ticker]/page.tsx:72-98`, `stocks.py:125,187,201`, `chart.py:105,213`

#### `/dashboard/analytics`, `/rebalance`, `/journal` (분석 화면들)

DB-only API 가 대부분 (분석은 미리 계산된 데이터 위주). staleTime 1h (3,600,000ms) 광범위 적용. **KIS 호출 거의 없음**.

#### 백그라운드 (사용자 트리거 외)

- `scheduler_market_jobs.py`: 매일 시장 마감 후 snapshot 저장 — 시간외 트래픽이라 안전.
- SSE 스트림: 30초마다 보유종목 currentprice push (`prices.py:271`). 사용자가 1명이라도 대시보드를 켜 두면 30초마다 N콜 KIS.

### 2.2 화면 간 중복 호출 (Critical)

#### 시나리오 A: 대시보드 → 포트폴리오 상세 이동

| 순서 | 호출 | 캐시 결과 |
|------|------|----------|
| 1. `/dashboard` 진입 | `fetch_domestic_price_detail` → KIS (**no cache check**) → 결과를 `price:{ticker}` 에 300s TTL 쓰기 (`dashboard.py:158-160`) | KIS N콜 |
| 2. 5초 뒤 `/portfolios/[id]` 클릭 | `get_or_fetch_domestic_price` → `price:{ticker}` 캐시 hit (`kis_price.py:501-503`) | **KIS 0콜** ✓ |
| 3. 30초 뒤 `/dashboard` 폴링 | 다시 `fetch_domestic_price_detail` → KIS (no cache check) → 캐시 덮어쓰기 | KIS N콜 (낭비) |

**결론**: 화면 A→B 한 번 이동 만으로는 중복 호출이 즉시 발생하지 않음. **문제는 대시보드의 30초 폴링이 캐시를 무시하는 패턴**.

#### 시나리오 B: 종목 상세 페이지

| 순서 | 호출 | 캐시 결과 |
|------|------|----------|
| 1. `/dashboard/stocks/AAPL` 진입 | `stocks.py:_fetch_overseas_detail` → `await client.get(...)` 직접 — **캐시 체크 없음, rate-limit 없음, retry 없음** | KIS 호출 (rate token 미차감) |
| 2. 뒤로가기 → `/dashboard` | `_fetch_prices` 가 같은 ticker 의 현재가 재조회 — 또 KIS | KIS 호출 (중복) |

`stocks.py` 의 detail 엔드포인트는 추가로 day_change_rate, w52_high, PER 등을 조회하는데, **이 데이터들은 어디에도 캐시되지 않음**. 같은 종목 페이지를 5초 뒤 다시 열면 또 KIS 호출.

#### 시나리오 C: 동시 다중 사용자 9시 장 시작

KIS rate limit 정책 (실전투자): **계정당 18 req/s** (token 발급 1 req/s 별도).
현재 코드 `KIS_RATE_LIMIT_PER_SEC=5`, `KIS_RATE_LIMIT_BURST=12`, `KIS_MAX_CONCURRENCY=6`. (`config.py:49-55`)

⚠️ **현재 설정은 KIS 정책의 28%만 사용** — 보수적으로 잡혀 있어 헤드룸은 있으나, 실제 병목은 backend 의 single-instance asyncio scheduler 가 모든 사용자 요청을 직렬화하는 부분.

1000명 동시 대시보드 진입 시:
- 각 사용자 평균 holding 10개 가정 → 10,000 ticker 요청
- 보유 종목 중복 제거 후 unique 종목 평균 ~500개 가정 → 500 KIS 호출 필요
- 5 req/s 로 직렬화 시 100초 소요 → **첫 진입 사용자는 빠르고, 뒤로 갈수록 점진적 슬로다운**
- token bucket 의 `_next_release` 예약 메커니즘 (`kis_rate_limiter.py:130-138`) 이 staircase 묶음 발사 방지 → 페어 분배 OK

**결론**: rate limit 자체는 9시 폭주에서 KIS 보호 정상 작동. 문제는 **사용자 perceived latency** — backend 단일 KIS 응답이 30s+ 걸릴 수 있음.

### 2.3 캐싱 정책 매트릭스

#### 백엔드 Redis 캐시

| Key 패턴 | TTL | 무효화 | 호출자 | 비고 |
|---------|-----|--------|--------|------|
| `price:{ticker}` | 30s holdings / 300s adaptive (장중) / 24h 장외 | TTL 만료만 | `_cache_price`, `get_or_fetch_*` | **current price 만** 저장. day_change/52w 미캐시 |
| `cash_balance:{portfolio_id}` | 30s | 주문시 (`orders.py:222`) | `/portfolios/{id}/cash-balance` | |
| `cash_balance:account:{account_id}` | 30s | 주문시 + 명시적 | aggregator (신규) | |
| `cash_summary:user:{user_id}` | 30s | 주문시 | `/dashboard/cash-summary` (신규) | |
| `kis:token:{hash16}` | TTL = 만료 - 10min | 401/500 응답 시 evict | `get_kis_access_token` | 24h 토큰 |
| `fx:USDKRW` | 1h fresh | 외부 호출 성공시 갱신 | `fetch_usd_krw_rate` | |
| `fx:USDKRW:stale` | 7d fallback | — | 위의 staleness fallback | |
| (dashboard ETag) | 메모리 only (sha256) | refresh=true bypass | `/dashboard/summary` | **계산 후 ETag — KIS 콜은 이미 발생** |

**근거**: `kis_price.py:41-45`, `kis_token.py:33,42`, `kis_fx.py:25-29`, `orders.py:60`, `cash_balance_aggregator.py:34-38`, `dashboard.py:406-414`

#### 프론트엔드 React Query

| 영역 | staleTime | gcTime | Persistence |
|------|-----------|--------|------------|
| 전역 default | 30s | 24h | — |
| 명시적 적용 prefix | — | — | `portfolios`, `portfolios-with-prices`, `holdings`, `analytics` → localStorage |
| `["dashboard","summary"]` | 60s | 24h | 미persist (실시간성) |
| `["portfolios",id,"holdings"]` | 기본 30s | persist | |
| 분석 차트류 | 60min (3,600,000ms) | persist | 의도적 장기 캐시 |

**근거**: `QueryProvider.tsx:14-19,27-33,38-56`, `page.tsx:258`, `AnalysisSection.tsx:47,59,66`

#### 미적용/취약 구간

1. **`/stocks/{ticker}/detail` 전체** — 백엔드 캐시 없음, 프론트 React Query 도 안 씀 (axios `useEffect`).
2. **`/chart/daily`** — 백엔드 캐시 없음. 차트는 일별 데이터라 1h+ 캐시 가능.
3. **대시보드 가격 조회** — `fetch_domestic_price_detail` 이 cache-first 아님.
4. **52주 고/저, day_change_rate, PER/PBR** — `price:{ticker}` 키는 current 만 저장 → detail 페이지가 매번 KIS 직격.

### 2.4 Rate limit + 동시성 분석

#### 정책 비교

| 항목 | KIS 정책 | 현재 코드 | 격차 |
|------|---------|----------|------|
| Per-second per account | 18/s (실전) / 10/s (모의) | 5.0/s (`config.py:49`) | 매우 보수적 (28%) |
| Burst | 18 within 1s window | 12 (`config.py:50`) | OK |
| 동시 in-flight | (명시 안 됨, ConnectTimeout 경험적) | 6 (`config.py:55`) | OK |
| Token issuance | 1/s | 1/s, burst 1 (`config.py:57-58`) | 매칭 |
| Retry on 429/EGW00201 | 즉시 재시도 권장 | 1회 + 50-150ms jitter (`kis_retry.py:28-29,109`) | OK |
| Retry on network error | (정책 무) | 1회 + 200-500ms jitter | OK |

#### Rate limit 적용 누락 — 호출 site 전수 조사

| 파일 | Rate limit | Concurrency cap | 비고 |
|------|-----------|-----------------|------|
| `kis_price.py` (6 sites) | ✓ `kis_call_slot` | ✓ | 이상적 패턴 |
| `price_snapshot.py:42` | ✓ `_rate_limit_acquire` | ✗ | dashboard `_fetch_prices` 가 사용 — **concurrency 미적용** |
| `kis_balance.py:91-99,200-208,296-303` | ✗ **누락** | ✗ | **신규 cash-summary 영향** |
| `kis_dividend.py:113,153` | ✓ acquire | ✗ | |
| `kis_order_query.py:102,201,326` | ✓ acquire | ✗ | |
| `kis_transaction.py:63,128` | ✓ acquire | ✗ | |
| `kis_benchmark.py:77,140` | ✓ acquire | ✗ | |
| `kis_account.py:63,166` | ✓ `kis_call_slot` | ✓ | |
| `stocks.py:125,187,201` | ✗ **누락** + retry 도 없음 | ✗ | **종목 상세 페이지 전체** |
| `chart.py:105,213` | ✗ **누락** + retry 도 없음 | ✗ | **차트 전체** |
| `kis_order_place.py:147` (POST) | ✗ | ✗ | 주문 — 의도일 가능성 (중복 위험), 그러나 rate 는 적용해야 |
| `kis_order_cancel.py:81` (POST) | ✗ | ✗ | 동일 |

#### 9시 폭주 시나리오

1. **현재 동작**: `kis_rate_limiter` 의 `_next_release` 시간 예약으로 N번째 대기자가 (N-12)/5 초 뒤 발사 → fair queuing. timeout 카운터 (`_timeout_counter`) 로 관찰 가능.
2. **약점**: 같은 ticker 를 1000명이 동시 요청하면 **request coalescing 부재** → 1000 KIS 호출 (캐시 hit 사이 race). Redis 캐시 set 직후 미세 윈도우에서 다수 cache miss 발생.
3. **graceful degradation**: `get_kis_availability()` 가 80% 실패 감지 시 자동으로 캐시-only 모드 전환 (`kis_price.py:337,365-373`). 좋은 안전망.
4. **dashboard `_fetch_prices` 의 20s 글로벌 타임아웃** (`dashboard.py:134`) — Cloudflare 30s cap 회피용. 정상.

### 2.5 프론트엔드 데이터 흐름

#### Query Key 정책 평가

페이지마다 **prefix 가 다르고 cross-page invalidation 시 광범위 invalidate** (`useOrders.ts:251-256`):
```ts
queryClient.invalidateQueries({ queryKey: ["portfolios", portfolioId, "holdings"] });
queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
queryClient.invalidateQueries({ queryKey: ["dashboard"] });
queryClient.invalidateQueries({ queryKey: ["cash-balance", portfolioId] });
```

**Over-invalidation 위험**: 단일 주문 settle 이 모든 사용자 페이지 캐시를 무효화 → 다음 진입 시 모두 fresh fetch.

#### SSE vs Polling 동시 동작

`page.tsx:257` 의 똑똑한 패턴:
```ts
refetchInterval: streamActive ? false : REFRESH_INTERVAL_MS,
```
SSE 연결 시 폴링 중단. **OK — 중복 없음**. 단, SSE 가 disconnect 되면 즉시 polling 으로 fallback.

#### localStorage 캐시 hydration

`QueryProvider.tsx:14-19,38-56`:
- portfolios, holdings, analytics 만 localStorage persist (24h)
- 새로 고침 시 **이전 데이터 즉시 표시** → SSR/refetch 동안 사용자에게 stale-but-fast UX
- dashboard summary 는 persist 안 함 — 실시간성 우선

**개선 가능**: 새로고침 시 dashboard summary 도 stale 가능 (마지막 값 보여주고 폴링)이지만 trade-off.

#### Prefetch 미활용

`<Link href="/dashboard/portfolios/[id]">` 가 다수 (`page.tsx:602`, `journal/page.tsx` 등). Next.js Link 는 viewport 진입 시 prefetch 하지만 **React Query 데이터는 prefetch 안 됨**. `queryClient.prefetchQuery` 활용 시 카드 hover 단계에서 backend 캐시 워밍 가능.

---

## 3. 수정 계획 (우선순위별)

### 🔴 P0 — 즉시 적용 (안정성 위협)

#### P0-1: `kis_balance.py` 3 곳에 rate limit 추가
- **현재**: 직접 `await kis_get(...)` 호출, rate token 미차감
- **수정**: 각 KIS 호출 직전 `async with kis_call_slot():` 래핑
- **예상 효과**: 9시 폭주 시 cash-summary 호출로 KIS 429 발생 차단. 다중 계좌 사용자가 대시보드 진입 시 leak 차단.
- **위치**: `kis_balance.py:91-99, 200-208, 296-303`
- **공수**: 30분

#### P0-2: `stocks.py`, `chart.py` 에 rate limit + retry 적용
- **현재**: `await client.get()` 직접 호출. KIS 429 시 즉시 실패.
- **수정**: `kis_get` 으로 교체 + `kis_call_slot` 래핑
- **예상 효과**: 종목 상세/차트 페이지가 KIS rate limit 정책 준수. 9시 폭주 시 retry 로 회복.
- **위치**: `stocks.py:125, 187, 201`, `chart.py:105, 213`
- **공수**: 1시간 (테스트 포함)

### 🟠 P1 — 단기 (1주일 내)

#### P1-1: 대시보드 `_fetch_prices` 를 cache-first 로 전환
- **현재**: `fetch_domestic_price_detail` / `fetch_overseas_price_detail` 직접 호출 → 항상 KIS
- **수정**: 새 함수 `get_or_fetch_domestic_price_detail` 도입 — `price:{ticker}` 캐시 hit + day_change/52w 별도 키 `price_detail:{ticker}` (TTL 30s 장중)
- **데이터 정합성**: 30s TTL 은 SSE 30s push 와 동기 — stale 위험 작음
- **예상 효과**: dashboard refetch 의 KIS 호출 95% 감소 (30s 첫 진입만 fresh, 이후 캐시 hit). 9시 폭주 latency 개선.
- **위치**: `dashboard.py:139-148`, `kis_price.py` 신규 함수
- **공수**: 4시간

#### P1-2: `/stocks/{ticker}/detail` 백엔드 캐시 도입
- **현재**: 캐시 0. 매 요청 KIS
- **수정**: `stock_detail:{ticker}` Redis 키 (TTL 30s 장중 / 5min 장외). day_change/52w/PER/PBR 모두 포함
- **예상 효과**: 같은 종목 5초 이내 재진입 → 캐시 hit. 종목 비교/검색 워크플로우 가속화.
- **공수**: 3시간

#### P1-3: `/chart/daily` 캐시 + ETag
- **현재**: 캐시 0. 매 요청 KIS daily-chart 호출
- **수정**: `chart_daily:{ticker}:{period}` Redis 키 (TTL = 장중 5min, 장외 1h, 과거 데이터 24h). Last-Modified/ETag 추가
- **예상 효과**: 차트는 일별 데이터라 캐시 hit rate 매우 높음. KIS chart 호출 80%+ 감소.
- **공수**: 4시간

#### P1-4: Single-flight (request coalescing) — Redis lock
- **현재**: 같은 ticker 를 N명이 동시 요청 시 N번 KIS 호출
- **수정**: `_fetch_prices` 진입 시 ticker 별 Redis SETNX lock (1s) — 락 보유자만 KIS 호출 후 캐시 쓰기. 나머지는 짧은 polling 으로 캐시 hit 대기.
- **예상 효과**: 9시 폭주 시 인기 종목 N→1 호출. KIS 트래픽 50%+ 감소 가능.
- **위치**: `kis_price.py` 신규 헬퍼
- **공수**: 8시간 (테스트 + 부분 실패 처리)

#### P1-5: 대시보드 `_fetch_prices` 에 `kis_call_slot` 적용 (concurrency cap)
- **현재**: `price_snapshot.py` 는 `_rate_limit_acquire` 만 사용 — concurrency 미적용
- **수정**: `_rate_limit_acquire` 호출 부분을 `kis_call_slot` 으로 교체 (legacy 서비스 일괄)
- **예상 효과**: 다중 사용자 동시 대시보드 진입 시 KIS connection 수 무한 증가 방지 (ConnectTimeout 차단).
- **위치**: `price_snapshot.py`, `kis_balance.py`, `kis_dividend.py`, `kis_order_query.py`, `kis_transaction.py`, `kis_benchmark.py`
- **공수**: 2시간

### 🟡 P2 — 중기 (2-4주)

#### P2-1: Rate limit 설정값 상향 조정
- **현재**: 5/s, burst 12 (KIS 정책 18/s 의 28%)
- **수정**: 12/s, burst 18 로 상향 (3-stage roll-out: 8/s → 12/s → 모니터링)
- **예상 효과**: dashboard refetch 직렬화 시간 60% 단축
- **선행조건**: P1-5 (concurrency cap) 완료 + Sentry/Grafana 모니터링 강화
- **공수**: 1시간 (config 변경) + 모니터링 일정

#### P2-2: Frontend prefetch — Link hover 시 query 워밍
- **현재**: `/dashboard/portfolios` 카드 클릭 시 fresh fetch
- **수정**: 포트폴리오 카드에 `onMouseEnter`/`onFocus` 시 `queryClient.prefetchQuery` (holdings, cash-balance)
- **예상 효과**: 클릭 → 표시 latency 200-400ms 단축 (perceived 즉시 표시)
- **공수**: 3시간

#### P2-3: Query key normalization — cross-page 캐시 공유
- **현재**: dashboard 의 `s.holdings` 와 `["portfolios", id, "holdings"]` 가 별도 query
- **수정**: 글로벌 `["prices", ticker]` query 도입 — dashboard 와 portfolio 가 같은 queryFn 공유
- **예상 효과**: 페이지 전환 시 React Query 레이어에서 즉시 캐시 hit (backend 까지 안 감)
- **공수**: 6시간

#### P2-4: 분석 화면 ETag/304 적용
- **현재**: dashboard summary 만 ETag (`dashboard.py:399-414`)
- **수정**: `/analytics/*` 엔드포인트도 동일 패턴 적용 (DB 데이터라 hash 안정적)
- **예상 효과**: 1시간 caching + 304 응답으로 bandwidth 90% 절감
- **공수**: 4시간

### 🔵 P3 — 장기 (이후 검토)

#### P3-1: 종목 마스터 정보 별도 캐시 (1일 TTL)
종목명/거래소/통화 등 정적 데이터는 `stock_meta:{ticker}` 키로 24h 캐시. 검색 결과/Holding 화면에서 활용.

#### P3-2: SSE 외부 broker (Redis Pub/Sub) 도입
현재 SSE 는 per-connection KIS 폴링. 다수 사용자 같은 종목 보유 시 KIS 호출 분산 불가. Pub/Sub 도입 시 1개 worker 가 KIS 호출 후 broadcast → 사용자 N → KIS 1.

#### P3-3: Stale-while-revalidate 패턴
캐시 만료 직후 진입한 사용자에게 stale 데이터를 즉시 응답 + 백그라운드에서 fresh fetch. perceived latency 0.

---

## 4. 구현 로드맵

### Sprint 1 (이번 주 — 안정성 우선)
- [x] ~~`/dashboard/cash-summary` 신규 + 예수금 표시~~ (이미 완료)
- [ ] **P0-1**: `kis_balance.py` rate limit 적용 (30분)
- [ ] **P0-2**: `stocks.py`, `chart.py` rate limit + retry (1시간)
- [ ] **P1-5**: 모든 legacy `acquire()` → `kis_call_slot` 일괄 교체 (2시간)
- **목표**: 9시 폭주 시 KIS 429 0 건 보장

### Sprint 2 (1주차 종료 ~ 2주차 초)
- [ ] **P1-1**: 대시보드 cache-first 전환 (4시간)
- [ ] **P1-2**: `/stocks/{ticker}/detail` 캐시 (3시간)
- [ ] **P1-3**: `/chart/daily` 캐시 (4시간)
- **목표**: 화면 전환 KIS 중복 호출 0. 사용자 perceived latency 50% 감소

### Sprint 3 (3주차)
- [ ] **P1-4**: Single-flight (request coalescing) — Redis lock (8시간)
- [ ] **P2-1**: Rate limit 12/s 로 상향 (단계적)
- **목표**: 다중 사용자 동시 진입 시 같은 종목 KIS 호출 1회로 수렴

### Sprint 4 (4주차 — UX 개선)
- [ ] **P2-2**: Frontend prefetch (3시간)
- [ ] **P2-3**: Query key normalization (6시간)
- [ ] **P2-4**: Analytics ETag (4시간)
- **목표**: 페이지 전환 perceived latency 200ms 이하

### 모니터링 지표 (Sprint 별 측정)

| 지표 | 측정 위치 | 목표 |
|------|----------|------|
| KIS 429/EGW00201 발생 횟수 | Sentry / `kis_retry.py:111` 로그 | Sprint 1 후 0/day |
| `_timeout_counter` (rate-limit timeout 누적) | `kis_rate_limiter.py:56` | Sprint 2 후 < 10/day |
| Dashboard summary p95 latency | Sentry transaction | Sprint 2 후 < 1.5s (현재 추정 3-5s) |
| KIS 호출 총량 (장중 1h 윈도) | Grafana | Sprint 3 후 30% 감소 |
| `price:{ticker}` 캐시 hit ratio | Redis INFO stats | Sprint 3 후 > 85% |

### 데이터 정합성 (Stale Data) 위험 평가

| 데이터 | 권장 TTL | Stale 영향 |
|--------|---------|-----------|
| 현재가 (current) | 30s 장중 | 30초 stale → SSE 가 보정 |
| Day change rate | 30s 장중 | 30초 stale 허용 |
| 52주 고/저 | 1h | 1시간 stale OK (월간 단위) |
| PER/PBR | 24h | 일단위 변동 |
| 예수금 | 30s | 주문 즉시 invalidate (이미 적용) |
| 환율 | 1h | 환차익 표시는 환차익 정확도보다 사용자 안내 우선 |
| 종목 마스터 (이름/거래소) | 24h | 거의 불변 |

**Stale 위험 가장 큰 곳**: 사용자 매수 직후 대시보드 진입 시 holdings 표시는 즉시 갱신되어야 함 → `["portfolios", id, "holdings"]` invalidation 이미 적용 (`useOrders.ts:254`). OK.

---

## 5. 부록 — 주요 코드 인용

### `dashboard.py:139-148` — 캐시 우회 패턴 (수정 대상)
```python
domestic_tasks = [
    fetch_domestic_price_detail(t, app_key, app_secret, client)  # ← cache-bypass
    for t in domestic_tickers
]
overseas_tasks = [
    fetch_overseas_price_detail(t, ticker_to_market.get(t, "NAS"), app_key, app_secret, client)
    for t in overseas_tickers
]
```

### `kis_balance.py:91-99` — Rate limit 누락 (P0)
```python
try:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await kis_get(  # ← acquire() 없이 직격
            client,
            f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
            headers=headers,
            params=params,
        )
```

### `stocks.py:124-130` — Rate limit + retry 누락 (P0)
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(  # ← kis_get 아님, kis_call_slot 아님
        f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers,
        params=params,
    )
```

### `kis_rate_limiter.py:223-246` — 권장 패턴
```python
@asynccontextmanager
async def kis_call_slot(n: int = 1, timeout: Optional[float] = None):
    if settings.KIS_MOCK_MODE:
        yield
        return
    async with _concurrency_sem:
        await _limiter.acquire(n=n, timeout=timeout)
        yield
```

---

## 6. 결론 및 다음 액션

**현재 시스템의 강점**:
- 토큰 버킷 + concurrency semaphore + retry 등 인프라는 잘 갖춰져 있음
- 적응형 TTL, 가용성 모니터, ETag 등 고급 패턴 일부 도입됨
- KIS 가용성 자동 fallback (cache-only mode) 안전망 존재

**현재 시스템의 약점**:
- 인프라가 **일관되게 적용되지 않음** — 좋은 패턴은 `kis_price.py` 에만, 나머지 서비스는 legacy
- 대시보드 자체가 캐시를 무시하고 매번 fresh fetch — 가장 빈번한 호출 경로의 비효율
- 종목 상세/차트는 캐시도 rate limit 도 없음 — sprint 발화점

**즉시 권장 액션**: Sprint 1 (P0-1, P0-2, P1-5) 만으로도 9시 폭주 안정성을 큰 폭으로 개선 가능. 총 공수 ~3.5 시간. 시작할 준비 되는 대로 `/feature` 또는 `/sprint` 로 진행 권장.
