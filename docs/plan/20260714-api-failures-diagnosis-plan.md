# API 대량 실패 진단 · 실행 계획 (2026-07-14)

> 작성 배경: "서버에서 많은 API 실패를 내리고 있다"는 보고.
> **제약**: 이 계획을 작성한 세션은 클라우드 격리 컨테이너에서 실행되어
> `ssh mac-mini` 로 라이브 로그에 직접 접근할 수 없다. 아래 진단 명령은
> **사용자가 로컬 머신(mac-mini SSH 가능 환경)에서 직접 실행**해야 하며,
> 출력이 확보되는 즉시 원인이 특정되고 §3 의 해당 수정안으로 넘어간다.

---

## 1. 코드 근거로 좁힌 유력 원인 (우선순위순)

각 가설은 서로 다른 로그 시그니처를 남기므로 §2 스크립트 한 번으로 구분된다.

### H1 — KIS 토큰 발급 실패 (가장 유력, "서버는 살아있는데 전부 실패")
- `check_kis_api_health()` 는 base URL 에 **HEAD 1회**만 보내고 *어떤 HTTP
  응답이든* "가용"으로 판정한다 (`kis_health.py:61-68`). 즉 **인증/토큰
  발급 실패는 감지하지 못한다** → `is_available=True` 유지 → 30초 자동복구
  잡도 발동 안 함 → 모든 실 호출이 조용히 계속 실패.
- 토큰 발급이 깨지면(`_issue_token`, `kis_token.py:110-128`) 모든 시세/잔고/
  주문 호출이 연쇄 실패한다. 흔한 원인: `EGW00133`(토큰 과다요청),
  appkey/secret 만료·회전, KIS 정기점검.
- **로그 시그니처**: `KIS token endpoint returned HTTP <4xx/5xx>`,
  `KIS token endpoint returned unexpected response format`, `EGW00133`.

### H2 — 레이트리밋 폭주 (EGW00201 / 429)
- 토큰버킷 5/s·burst 20 (`kis_rate_limiter.py`). SSE 30s push + 대시보드
  폴링 + preload 잡이 겹치면 burst 소진 → `acquire` 타임아웃 또는 KIS 가
  `EGW00201`/`429` 반환. `kis_retry.py` 가 재시도하지만 한도 초과 시 실패로
  올라온다.
- **로그 시그니처**: `P95 slow acquire`, `retry N/M ... rate-limited`,
  `EGW00201`, `429`.

### H3 — 가용성 래치가 캐시 전용 모드에 고착
- `fetch_prices_parallel` 이 벌크의 ≥80% 실패를 감지하면
  `set_kis_availability(False)` (`kis_price.py:377-385`) → 이후 KIS 스킵,
  Redis 캐시만 반환. 캐시 미스 종목은 `null` 가격 → 프론트에서 실패로 보임.
- 30초 `_kis_health_recheck_job` 가 복구를 시도하지만, **스케줄러가 안 돌거나**
  HEAD 는 성공하는데 실제 호출은 계속 실패하는 상황(H1/H2)이면 복구가
  체감되지 않는다.
- **로그 시그니처**: `bulk fetch failed .../... switching to cache mode`,
  `KIS API unavailable — returning cached prices`,
  `KIS API recovered`(복구 시).

### H4 — KIS 측 장애 / 정기점검 (우리 코드 무관)
- KIS 는 정기점검(대략 평일 23:40~00:10, 일요일 등) 및 간헐 5xx 가 있다.
  이 경우 컨테이너에서 KIS 로의 curl 자체가 timeout/5xx.
- **로그 시그니처**: `server-error` 재시도 로그, 컨테이너→KIS curl timeout.

### H5 — 백엔드 자체 지연/포화 (외부 아닌 내부 요인)
- `process_time_ms` 분포로 백엔드 자체 병목 vs 외부 대기를 구분.
- **로그 시그니처**: `request completed ... process_time_ms=` 상위값.

---

## 2. 진단 스크립트 (mac-mini 에서 실행 → 출력을 붙여주세요)

```bash
# ===== The Wealth API 실패 진단 번들 =====
B=the-wealth-backend-1

echo "########## [0] 컨테이너 상태 ##########"
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker stats --no-stream $B the-wealth-postgres-1 the-wealth-redis-1

echo "########## [H1] 토큰 발급 실패 ##########"
docker logs --since 1h $B 2>&1 | grep -iE "token endpoint returned|unexpected response format|EGW00133|token issued|near/past expiry" | tail -30

echo "########## [H2] 레이트리밋 폭주 ##########"
docker logs --since 1h $B 2>&1 | grep -iE "P95 slow acquire|rate-limited|EGW00201|429" | tail -40

echo "########## [H3] 가용성 래치 / 캐시 모드 ##########"
docker logs --since 2h $B 2>&1 | grep -iE "KisHealth|bulk fetch|switching to cache|KIS API unavailable|KIS API recovered|is_available" | tail -40

echo "########## [H4] KIS 도달성 (컨테이너 → KIS) ##########"
docker exec $B curl -sv --max-time 5 https://openapi.koreainvestment.com:9443/ 2>&1 | grep -E "Connected|SSL|HTTP|timed out|refused"

echo "########## [H5] 요청 지연 분포 (느린 요청 상위) ##########"
docker logs --tail 800 $B 2>&1 | grep "request completed" | grep -oE "path=[^ ]+ .*process_time_ms=[0-9]+" | sort -t= -k3 -n | tail -20

echo "########## [공통] 최근 에러/예외 ##########"
docker logs --since 1h $B 2>&1 | grep -iE "ERROR|Traceback|Exception|CRITICAL" | tail -40

echo "########## [공통] 실패 응답 상태코드 분포 ##########"
docker logs --since 1h $B 2>&1 | grep -oE "status=(4[0-9]{2}|5[0-9]{2})" | sort | uniq -c | sort -rn
```

---

## 3. 원인별 수정안 (로그 확인 후 진행)

| 확인된 시그니처 | 원인 | 즉시 조치 | 코드 수정 |
|---|---|---|---|
| `token endpoint returned HTTP 403/500`, `EGW00133` | H1 토큰 | Redis `kis:token:*` 키 확인·삭제 후 재발급 유도; appkey/secret 유효성 점검 | `check_kis_api_health()` 를 HEAD → **실제 토큰 발급 프로브**로 강화해 인증 실패도 `is_available=False` 로 반영 (아래 §4) |
| `P95 slow acquire`, `EGW00201` 다수 | H2 레이트 | 일시적으로 `KIS_RATE_LIMIT_PER_SEC`/burst 하향 또는 폴링 완화 | preload/SSE/폴링 스케줄 겹침 완화, 캐시 TTL 조정 |
| `switching to cache mode` 후 `recovered` 없음 | H3 래치 | `docker compose restart backend` 로 강제 리셋 | 스케줄러 헬스잡 동작 검증; H1 프로브 강화가 근본 해결 |
| 컨테이너→KIS curl timeout/5xx | H4 KIS 장애 | KIS 점검공지 확인, 자동복구 대기 | 조치 불필요(자가치유) |
| `process_time_ms` 상위가 특정 엔드포인트 | H5 내부 | 해당 엔드포인트 프로파일 | 쿼리/캐시 최적화 |

---

## 4. 권장 근본 수정 (H1 이 확인될 경우 — 코드 개선 후보)

`check_kis_api_health()` 는 현재 base URL HEAD 성공만으로 가용 판정하여
**토큰/인증 계층 실패를 놓친다**. 이것이 "서버는 200 을 주는데 시세 API 는
전부 실패" 를 자가치유 못하게 만드는 핵심 갭이다.

- **개선**: 헬스 프로브를 "HEAD 도달성 + (짧은 주기로) 토큰 발급 성공 여부"
  2단계로 확장. 토큰 발급 실패가 지속되면 `is_available=False` 로 내려
  캐시 전용 모드 + 30초 복구 루프가 정상 작동하도록 한다.
- **주의**: 토큰 발급 프로브는 KIS `EGW00133`(과다요청) 유발을 피하기 위해
  캐시된 토큰 재사용 경로를 타야 하며, 실패 시에만 강제 발급을 시도한다.
- TDD: `check_kis_api_health` — HEAD 성공 + 토큰 발급 실패 → `False` 반환
  케이스 테스트 추가.

> 이 수정은 로그로 H1 이 확인된 뒤 착수한다. 추측만으로 헬스체크 로직을
> 바꾸면 오히려 정상 트래픽에 토큰 발급 부하를 더할 수 있어, **진단 우선**.

---

## 5. 다음 단계

1. 사용자가 §2 스크립트를 mac-mini 에서 실행 → 출력 공유.
2. 시그니처로 H1~H5 확정 → §3 즉시 조치.
3. H1 확정 시 §4 헬스 프로브 강화를 TDD 로 구현·리뷰·배포.
