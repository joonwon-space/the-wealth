# 비용 관리

## 1. 개요

The Wealth는 외부 API(한국투자증권 KIS OpenAPI)에 의존하는 서비스로, API 호출량과 서버 리소스를 효율적으로 관리하는 것이 운영 비용에 직접적인 영향을 미칩니다. 이 문서에서는 KIS API 사용 최적화, Redis 캐싱 전략, 서버 리소스 관리에 대해 다룹니다.

---

## 2. KIS API 레이트 리밋 관리

### 2.1 KIS OpenAPI 제약사항

한국투자증권 OpenAPI는 호출 빈도에 제한이 있으며, 초과 시 일시적 차단될 수 있습니다:

| 항목 | 제한 |
|------|------|
| 초당 요청 수 | API별 상이 (일반적으로 1~2건/초) |
| 일일 요청 수 | 계정별 제한 |
| 토큰 유효기간 | 24시간 |

### 2.2 호출 최소화 전략

#### 병렬 배치 호출

개별 종목의 현재가를 순차적으로 호출하지 않고, `asyncio.gather()`로 **병렬 배치 처리**:

```
비효율적 (순차):
  종목1 조회 (200ms) → 종목2 조회 (200ms) → 종목3 조회 (200ms)
  총 소요: 600ms, 3회 호출

효율적 (병렬):
  종목1, 2, 3 동시 조회 (asyncio.gather)
  총 소요: ~200ms, 3회 호출 (동시)
```

병렬 처리는 호출 횟수 자체를 줄이지는 않지만, 동일 시간 내 처리량을 극대화하여 사용자 경험을 개선합니다.

#### 대시보드 폴링 주기

- 대시보드 데이터 갱신: **30초 주기**
- SSE 스트림: **30초 간격** 가격 업데이트
- 장외 시간(KST 15:30 이후): SSE 비활성화로 불필요한 호출 차단

#### 스케줄러 최적화

```
kis_sync (1시간 간격):
  - 사용자별 순차 처리 (동시 요청 폭주 방지)
  - KIS 자격증명이 없는 사용자 건너뜀
  - 포트폴리오가 없는 사용자 건너뜀

daily_close_snapshot (KST 16:10, 평일):
  - 보유 종목 ticker 중복 제거 (distinct)
  - 전체 종목 OHLCV 병렬 조회 (1회 배치)
  - OHLCV 실패 시 현재가 폴백 (2차 시도)
```

---

## 3. 토큰 로테이션 캐싱

### 3.1 KIS OAuth2 토큰 캐싱

KIS 토큰은 24시간 유효하지만, 매 API 호출마다 새로 발급받으면 비효율적입니다. Redis 캐싱으로 토큰 재사용:

```
┌──────────────────────────────────────────────────┐
│ KIS 토큰 캐싱 전략                                │
│                                                   │
│ 1. 현재가 조회 요청 수신                           │
│ 2. Redis에서 캐시된 토큰 확인                      │
│    키: kis:token:{sha256(app_key)[:16]}           │
│                                                   │
│    ├─ 캐시 HIT → 즉시 사용 (0ms 지연)             │
│    │                                              │
│    └─ 캐시 MISS → KIS 토큰 발급 API 호출          │
│       POST /oauth2/tokenP                         │
│       응답: { access_token, expires_at }          │
│       Redis 저장: TTL = expires_in - 600초        │
│       (만료 10분 전 선제적 교체)                    │
│                                                   │
│ 3. 토큰으로 현재가 API 호출                        │
└──────────────────────────────────────────────────┘
```

### 3.2 TTL 계산

```python
TTL = max(expires_in_seconds - 600, 60)
```

- `expires_in`: KIS 응답의 `access_token_token_expired` 파싱
- 600초(10분) 버퍼: 만료 직전 요청 실패 방지
- 최소 60초: 파싱 실패 시 안전 하한
- 기본 폴백: 파싱 불가 시 86,400초 (24시간)

### 3.3 캐시 키 설계

```
kis:token:{sha256(app_key)[:16]}
```

- `sha256(app_key)[:16]`: App Key 해시의 첫 16자
- 사용자별 독립 캐시 (크로스-유저 캐시 충돌 방지)
- 키 길이 최소화 (Redis 메모리 절약)

### 3.4 강제 무효화

`invalidate_kis_token(app_key)` 함수로 캐시 토큰 즉시 삭제 가능:
- KIS API 인증 오류 발생 시 사용
- 사용자가 KIS 자격증명 변경 시 사용

---

## 4. Redis 효율성

### 4.1 Redis 키 패턴 전체 현황

| 키 패턴 | 값 타입 | TTL | 용도 | 메모리 영향 |
|---------|--------|-----|------|------------|
| `refresh_jti:{uuid}` | string (user_id) | 7일 | JWT refresh token JTI | 낮음 (사용자 수 비례) |
| `kis:token:{hash16}` | string (access_token) | ~23.8시간 | KIS OAuth2 토큰 캐시 | 매우 낮음 (계좌 수 비례) |
| `price:{ticker}` | string (Decimal) | 300초 | 현재가 캐시 | 낮음 (보유종목 수 비례) |
| `mst:stock_list` | JSON array | 24시간 | KRX 종목 마스터 | 중간 (수천 종목) |

### 4.2 현재가 캐시 전략

```
현재가 조회 요청
  │
  ▼ KIS API 호출 시도
  ├─ 성공 → 가격 반환 + Redis 캐시 갱신 (TTL 300초)
  │
  └─ 실패 → Redis 캐시 조회 (폴백)
     ├─ 캐시 HIT → 캐시된 가격 반환 (최대 5분 전 가격)
     └─ 캐시 MISS → None 반환
```

핵심 설계:
- **Write-through**: KIS API 성공 시 즉시 Redis에 저장
- **TTL 300초 (5분)**: 장중 가격 변동 반영과 API 절약의 균형점
- **Graceful degradation**: KIS API 장애 시 캐시 폴백으로 서비스 연속성 보장

### 4.3 종목 마스터 캐시

앱 시작 시 KRX + ETF 전체 종목 목록을 Redis에 프리로드:

```
앱 시작 (lifespan)
  │
  ▼ _load_stock_list()
  │
  ▼ Redis 저장: mst:stock_list → JSON array
  │  TTL: 24시간
  │
  ▼ 종목 검색 시 Redis에서 조회 (DB 조회 불필요)
```

- 검색 성능: O(1) Redis 조회 → 수천 종목 즉시 필터링
- 갱신 주기: 24시간 (일 1회 자동 갱신)

### 4.4 메모리 사용량 추정

| 키 타입 | 예상 건수 | 키당 크기 | 총 추정 메모리 |
|---------|----------|----------|--------------|
| refresh_jti | ~10 (활성 사용자) | ~100B | ~1KB |
| kis:token | ~5 (KIS 계좌) | ~500B | ~2.5KB |
| price | ~50 (보유종목) | ~80B | ~4KB |
| mst:stock_list | 1 | ~500KB | ~500KB |
| **합계** | | | **~510KB** |

개인 자산관리 서비스 특성상 Redis 메모리 사용량은 매우 적습니다.

---

## 5. 리소스 최적화

### 5.1 Docker 이미지 크기 최적화

| 서비스 | 베이스 이미지 | 최적화 |
|--------|-------------|--------|
| Backend | `python:3.12-slim` | 멀티 스테이지 빌드, gcc 미포함 |
| Frontend | `node:20-alpine` | 3단계 빌드, standalone 출력 |
| PostgreSQL | `postgres:16-alpine` | Alpine 기반 |
| Redis | `redis:7-alpine` | Alpine 기반 |

### 5.2 네트워크 최적화

- **Docker Compose 내부 네트워크**: 서비스 간 통신은 Docker 내부 DNS (외부 네트워크 불필요)
- **KIS API 연결**: `httpx.AsyncClient(timeout=10.0)` — 10초 타임아웃으로 행 방지
- **CORS**: 허용 Origin 제한 (`localhost:3000`, `joonwon.dev`)

### 5.3 데이터베이스 최적화

- **현재가 미저장**: 현재가/P&L은 KIS API에서 실시간 계산 → DB 저장 공간 절약
- **스냅샷 선택 저장**: 장 마감 OHLCV만 `price_snapshots`에 저장 (일 1회)
- **유니크 제약**: `(ticker, snapshot_date)` 유니크 → 중복 스냅샷 방지
- **Cascade 삭제**: 사용자 삭제 시 관련 데이터 자동 정리

### 5.4 프론트엔드 최적화

- **Next.js standalone**: node_modules 없이 서버 실행 (이미지 크기 대폭 감소)
- **SSR**: Server Components로 초기 로드 최적화
- **SSE 장외 비활성화**: KST 09:00~15:30 외 시간에는 SSE 연결 비활성화

### 5.5 CI/CD 비용 관리

- **경로 기반 트리거**: `paths: ['backend/**']` / `paths: ['frontend/**']`로 변경 없는 서비스 빌드 건너뜀
- **캐시 활용**: Python pip 캐시, npm 캐시로 의존성 설치 시간 단축
- **Self-hosted runner**: 배포용 runner를 자체 서버에서 운영 → GitHub Actions 분 사용량 절감
- **Docker parallel build**: `docker compose build --parallel`로 빌드 시간 단축
- **Image prune**: 배포 후 미사용 이미지 자동 정리

---

## 6. 모니터링 및 가시성

### 6.1 동기화 로그

`sync_logs` 테이블에 모든 동기화 결과 기록:

```
성공: { status: "success", inserted: 2, updated: 5, deleted: 1 }
실패: { status: "error", message: "KIS API timeout..." }
```

- 동기화 실패 패턴 분석 가능
- API 호출 실패율 추적

### 6.2 구조화 로깅

structlog 기반 로깅으로 주요 이벤트 추적:

```
[Scheduler] Starting periodic KIS account sync
[Scheduler] Synced user=1 portfolio=1: +2 ~5 -1
[Scheduler] Sync failed user=2: KIS API timeout
KIS token issued, TTL=85800s (expires=2026-03-19 15:30:00)
Using cached price for 005930: 68000
```

- 매 요청에 `X-Request-ID` 부여로 요청 추적
- 로그 레벨별 필터링: INFO(정상), WARNING(폴백), ERROR(장애)

---

## 관련 문서

- [프로젝트 분석](analysis.md) -- KIS API 비동기 병렬 호출 아키텍처
- [인프라](infrastructure.md) -- Docker, CI/CD, Redis 구성
