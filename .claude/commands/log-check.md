---
description: 최근 1시간 서버 로그를 분석해 이상 징후를 감지하고 docs/alerts/에 저장한다. 이상 없으면 조용히 종료.
---

# Log Check

최근 1시간 백엔드 로그를 분석해 이상 징후를 감지한다.
이상이 있으면 `docs/alerts/YYYY-MM-DD-HH.md`에 저장하고 수정을 요청한다.
이상이 없으면 아무것도 하지 않고 조용히 종료한다.

## 로그 수집

Docker가 실행 중인 경우 (프로덕션/로컬 공통):
```bash
docker compose logs backend --since 1h --no-log-prefix 2>/dev/null
```

파일 로그가 있는 경우 (LOG_DIR 설정 시):
```bash
# 컨테이너 내부 로그 파일 직접 읽기
docker compose exec backend tail -n 2000 /var/log/the-wealth/app.log 2>/dev/null
```

둘 다 없으면 사용자에게 로그 접근 방법을 물어본다.

## 이상 징후 감지 기준

수집한 로그에서 다음 패턴을 탐지한다:

### 🔴 Critical (즉시 수정 필요)
- `"level": "error"` 또는 `ERROR` 레벨 로그
- KIS API 오류: `rt_cd` 값이 `"0"`이 아닌 경우
- DB 연결 실패: `sqlalchemy`, `asyncpg`, `connection refused`
- Redis 연결 실패: `redis`, `ConnectionError`
- 인증 위조 시도: 짧은 시간 내 동일 IP의 로그인 실패 5회 이상
- 스케줄러 실패: `_consecutive_failures` 값이 3 이상
- 500 Internal Server Error 응답 3회 이상

### 🟡 Warning (주의 필요)
- `"level": "warning"` 또는 `WARNING` 레벨 로그
- KIS API 재시도 발생: `retrying`, `invalidating token`
- 응답 지연: 특정 엔드포인트 타임아웃 (`timeout`, `TimeoutError`)
- 401 응답 급증: 5분 내 10회 이상
- 캐시 미스 과다: Redis MISS가 HIT보다 많은 경우

### 🟢 Info (참고)
- 스케줄러 정상 실행 확인
- 동기화 건수 요약 (inserted/updated/deleted)
- 전체 요청 수 및 평균 응답 코드 분포

## 분석 방법

1. 로그를 수집한다
2. Critical 패턴부터 순서대로 탐색한다
3. 각 패턴별 발생 건수, 시간대, 대표 로그 1~3줄을 기록한다
4. Critical/Warning이 하나라도 있으면 → 알림 파일 생성
5. Info만 있거나 아무것도 없으면 → 조용히 종료 (파일 생성 안 함)

## 알림 파일 생성

이상 감지 시 `docs/alerts/` 디렉토리에 파일을 저장한다.

파일명: `YYYY-MM-DD-HH.md` (현재 시각 기준)

```markdown
# 로그 알림 — YYYY-MM-DD HH:00

**분석 범위**: 최근 1시간 (HH-1:00 ~ HH:00)
**감지 시각**: YYYY-MM-DD HH:MM KST

---

## 🔴 Critical

### [오류명]
- **발생 횟수**: N회
- **첫 발생**: HH:MM:SS
- **대표 로그**:
  ```
  (로그 원문 1~3줄)
  ```
- **추정 원인**: ...
- **수정 방향**: `파일경로:라인` — 구체적 수정 제안

---

## 🟡 Warning

### [경고명]
- **발생 횟수**: N회
- **대표 로그**: `...`
- **수정 방향**: ...

---

## 📊 통계 요약

| 항목 | 값 |
|------|-----|
| 전체 로그 라인 | N |
| ERROR | N |
| WARNING | N |
| 200 응답 | N |
| 4xx 응답 | N |
| 5xx 응답 | N |
| KIS API 호출 | N |
| KIS API 실패 | N |

---

## 수정 요청

위 이슈들을 확인하고 수정해주세요.
`/log-check` 재실행으로 해소 여부를 확인할 수 있습니다.
```

## 완료 출력

이상 감지 시:
```
⚠️  이상 감지 — docs/alerts/YYYY-MM-DD-HH.md 저장됨

Critical: N건
Warning: N건

주요 이슈:
- [간략 요약]
- [간략 요약]
```

이상 없을 시:
```
✅ 이상 없음 (YYYY-MM-DD HH:00 기준 1시간)
```
