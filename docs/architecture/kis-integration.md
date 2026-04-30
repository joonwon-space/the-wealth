# KIS Integration Reference

한국투자증권(KIS) OpenAPI 연동 세부 사항. 모든 수치는 소스 코드에서 직접 추출.

---

## 1. TR_ID 표

### 1.1 국내 주식 — 시세 조회

| TR_ID | 용도 | 파일:라인 |
|-------|------|----------|
| `FHKST01010100` | 국내주식 현재가 조회 | `kis_price.py:109` |
| `FHKST01010400` | 국내주식 일별 OHLCV | `kis_price.py:188` |

### 1.2 해외 주식 — 시세 조회

| TR_ID | 용도 | 파일:라인 |
|-------|------|----------|
| `HHDFS00000300` | 해외주식 현재가 조회 (기본) | `kis_price.py:135` |
| `HHDFS76200200` | 해외주식 52주 고/저가 조회 (fallback) | `kis_price.py:326` |

### 1.3 국내 주식 — 주문 (실전)

| TR_ID | 용도 | 계좌 유형 |
|-------|------|----------|
| `TTTC0802U` | 국내 매수 | 일반, ISA |
| `TTTC0801U` | 국내 매도 | 일반, ISA |
| `TTTC0852U` | 국내 매수 | 연금저축, IRP |
| `TTTC0851U` | 국내 매도 | 연금저축, IRP |
| `TTTC0803U` | 국내 주문 취소 | 모든 유형 |

출처: `kis_order_place.py:43-54`, `kis_order_cancel.py:40`

### 1.4 국내 주식 — 주문 (모의투자)

| TR_ID | 용도 |
|-------|------|
| `VTTC0802U` | 국내 매수 (모의) |
| `VTTC0801U` | 국내 매도 (모의) |

출처: `kis_order_place.py:57-58`

### 1.5 해외 주식 — 주문

| TR_ID | 용도 | 모드 |
|-------|------|------|
| `JTTT1002U` | 해외 매수 | 실전 |
| `JTTT1006U` | 해외 매도 | 실전 |
| `VTTT1002U` | 해외 매수 | 모의 |
| `VTTT1001U` | 해외 매도 | 모의 |

출처: `kis_order_place.py:61-64`

### 1.6 잔고 / 계좌

| TR_ID | 용도 | 모드 |
|-------|------|------|
| `TTTC8434R` | 국내주식 잔고 조회 | 실전 |
| `VTTC8434R` | 국내주식 잔고 조회 | 모의 |
| `TTTS3012R` | 해외주식 잔고 조회 | 실전/모의 |
| `CTRP6504R` | 해외주식 체결기준현재잔고 (USD 외화예수금 + 환율) | 실전 |
| `TTTC8908R` | 국내 미체결 주문 조회 | 실전 |
| `VTTC8908R` | 국내 미체결 주문 조회 | 모의 |
| `TTTC8001R` | 국내 거래 내역 | 실전 |
| `VTTC8001R` | 국내 거래 내역 | 모의 |
| `TTTC8036R` | 국내 당일 주문 내역 | 실전 |
| `TTTS3035R` | 해외 거래 내역 | 실전 |

출처: `kis_balance.py:64,193,264`, `kis_account.py:40,126`, `kis_order_query.py:77,146,256`, `kis_transaction.py:42,108`

---

## 2. KIS_MOCK_MODE 동작

`backend/app/core/config.py:50-52`:
```python
KIS_RATE_LIMIT_PER_SEC: float = 5.0
KIS_RATE_LIMIT_BURST: int = 15
KIS_MOCK_MODE: bool = False
```

`KIS_MOCK_MODE=True`로 설정하면:
- Rate limiter가 `_consume()` 호출 시 즉시 0을 반환 → **대기 없음** (`kis_rate_limiter.py:95`)
- 주문 TR_ID가 모의투자용(`VTTC*`, `VTTT*`)으로 자동 전환 (`kis_order_place.py:95-107`)
- KIS_BASE_URL은 `backend/.env`에서 별도로 모의투자 URL로 변경 필요:
  ```
  KIS_BASE_URL=https://openapivts.koreainvestment.com:29443  # 모의투자
  KIS_BASE_URL=https://openapi.koreainvestment.com:9443      # 실전
  ```

모의투자 / 실전 분리는 `is_paper_trading` 파라미터로 결정되며, KIS 계좌 설정에서 관리.

---

## 3. Rate Limiter — Token Bucket 파라미터

구현: `backend/app/services/kis_rate_limiter.py`

| 파라미터 | 기본값 | 설정 env var | 의미 |
|---------|--------|-------------|------|
| rate (초당 토큰) | `5.0` | `KIS_RATE_LIMIT_PER_SEC` | steady-state KIS 호출 속도 |
| burst (최대 버스트) | `15` | `KIS_RATE_LIMIT_BURST` | 시작 시 보유 토큰 / 상한선 (KIS 18/s 정책 반영) |
| mock_mode | `False` | `KIS_MOCK_MODE` | True이면 rate limit 비활성화 |

### 동작 원리
- 시작 시 버킷에 `burst`개(15) 토큰 보유
- 매 호출마다 `_consume(1)` — 토큰 부족 시 필요 대기 시간 계산
- 초당 `rate`개(5) 속도로 토큰 보충, 상한 `burst`
- P95 경고: 대기시간 > 0.1s이면 `[KisRateLimiter] P95 slow acquire` 로그 출력
- `get_timeout_counter()` — 누적 타임아웃 횟수 반환 (observability)

### 네트워크 단절 재시도 (KIS_HTTP_NETWORK_RETRY)

`KIS_HTTP_NETWORK_RETRY` (기본값: `1`) — `ConnectError` / `TimeoutException` 수신 시 재시도 횟수.
429/EGW00201 재시도인 `KIS_HTTP_MAX_RETRIES`와 별개 경로:
- `KIS_HTTP_MAX_RETRIES`: HTTP 레이어 속도 제한 응답 재시도
- `KIS_HTTP_NETWORK_RETRY`: TCP/TLS 연결 실패 재시도

네트워크 단절이 지속되면 `fetch_prices_parallel` 벌크 실패 감지 → `set_kis_availability(False)` → 캐시 전용 모드.
30초 interval `kis_health_recheck` 잡이 자동 복구 시도.

### 조정법
```bash
# backend/.env
KIS_RATE_LIMIT_PER_SEC=3.0   # KIS 측 제한에 맞게 낮춤
KIS_RATE_LIMIT_BURST=10      # 버스트 줄임

# 단위 테스트에서 mock_mode 사용 예시
limiter = KisRateLimiter(rate=10.0, burst=100, mock_mode=True)
```

### 호출 위치
모든 KIS HTTP 호출 전 `await acquire()` 필수 (`kis_rate_limiter.py:163`):
- `kis_price.py` — `fetch_domestic_price`, `fetch_overseas_price`, `fetch_domestic_daily_ohlcv`, `fetch_overseas_price_detail`
- `price_snapshot.py` — `fetch_domestic_price_detail`

---

## 4. KIS 토큰 Lifecycle

구현: `backend/app/services/kis_token.py`

```
앱 기동
    │
    ▼
get_kis_access_token(app_key, app_secret)
    │
    ├─ Redis에 캐시 존재? ──Yes──► 캐시 반환
    │
    No
    ▼
asyncio.Lock (per-key) 획득
    │
    ▼
POST {KIS_BASE_URL}/oauth2/tokenP
    │
    ▼
TTL = access_token_token_expired 파싱 (실패 시 86400s)
    │
    ▼
Redis setex(key, TTL - 600, token)   ← 10분 일찍 만료 처리
    │
    ▼
토큰 반환
```

**Redis 키 형식** (`kis_token.py:34-35`):
```python
key_hash = hashlib.sha256(app_key.encode()).hexdigest()[:16]
cache_key = f"kis:token:{key_hash}"
```
app_key 해시를 사용하므로 사용자별로 분리됨. 실제 app_key가 Redis 키에 노출되지 않음.

**만료 설정** (`kis_token.py:22-23`):
```python
_ROTATION_BUFFER_SECONDS = 600  # rotate 10 min before expiry
_TOKEN_TTL_SECONDS = 86400       # 24 h fallback (KIS spec)
```

**강제 갱신**:
```python
from app.services.kis_token import invalidate_kis_token
await invalidate_kis_token(app_key)  # Redis에서 삭제 → 다음 요청에 재발급
```

---

## 5. rt_cd / msg1 에러 코드 해석

KIS API 응답에서 `rt_cd` 필드로 성공 여부 판단:

| rt_cd | 상황 | msg1 예시 | 조치 |
|-------|------|----------|------|
| `0` | 성공 | 정상처리 | — |
| `1` | 토큰 만료 | "기간이 만료", "토큰이 유효하지 않습니다" | Redis 키 삭제 → 재발급 |
| `1` | 잘못된 APP_KEY | "접근토큰 발급 불가" | KIS 포털에서 APP_KEY 확인 |
| `1` | IP 차단 | "IP 차단", "허용되지 않은 IP" | KIS 포털 IP 화이트리스트 추가 |
| `1` | 주문 수량 오류 | "주문수량 오류" | 요청 quantity 재확인 |
| `1` | 잔고 부족 | "잔고부족" | 계좌 잔액 확인 |
| `1` | 장 마감 | "장 운영시간이 아닙니다" | KST 09:00~15:30 내에만 주문 가능 |

응답 파싱 패턴:
```python
data = response.json()
if data.get("rt_cd") != "0":
    msg = data.get("msg1", "Unknown KIS error")
    raise ValueError(f"KIS error: {msg}")
```

---

## 6. 국내 ↔ 해외 라우팅 결정 규칙

### 시세 조회 (`kis_price.py:253-259`)
`fetch_prices_batch()` 호출 시 `market` 파라미터로 결정:
```python
if market == "domestic":
    # fetch_domestic_price() → FHKST01010100
else:
    # fetch_overseas_price(ticker, market, ...) → HHDFS00000300
    # market 값 예: "NASD", "NYSE", "AMEX", "TKSE"
```

### 주문 (`kis_order_place.py`)
`exchange_code` 파라미터 기준:
- `exchange_code == ""` 또는 국내 → `place_domestic_order()` (TTTC0802U 계열)
- `exchange_code in ["NASD", "NYSE", "AMEX", ...]` → `place_overseas_order()` (JTTT1002U 계열)

해외 거래소 코드 예:
| 코드 | 거래소 |
|------|--------|
| `NASD` | NASDAQ |
| `NYSE` | New York Stock Exchange |
| `AMEX` | AMEX |
| `TKSE` | 도쿄증권거래소 |

---

## Related

- [`docs/architecture/auth-flow.md`](./auth-flow.md) — KIS 토큰이 JWT 인증과 어떻게 분리되는지
- [`docs/runbooks/troubleshooting.md`](../runbooks/troubleshooting.md) — KIS 403/IP 차단 해결 절차
- [`docs/architecture/feature-trading.md`](./feature-trading.md) — 주문 lifecycle, Redis 락
