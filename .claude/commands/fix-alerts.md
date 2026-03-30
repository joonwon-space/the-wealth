---
description: docs/alerts/ 의 미처리 알림을 읽고 원인을 파악해 코드를 수정한다.
---

# Fix Alerts

`docs/alerts/` 에 쌓인 로그 알림 파일을 읽고, 원인을 분석해 코드를 수정한다.

## 사용법

```
/fix-alerts               → 미처리 알림 전체 처리
/fix-alerts critical      → Critical 항목만 처리
/fix-alerts 2026-03-30    → 특정 날짜 알림만 처리
```

## 워크플로우

### 1. 미처리 알림 목록 수집

```bash
ls docs/alerts/*.md 2>/dev/null | grep -v ".gitkeep"
```

파일이 없으면:
```
✅ 처리할 알림이 없습니다.
```
종료.

파일이 있으면 각 파일을 읽어 다음을 파악한다:
- 심각도 (Critical / Warning)
- 발생 시각
- 이슈 종류 (KIS API 오류, DB 오류, 인증 오류 등)
- 이미 `[resolved]` 표시된 항목은 건너뜀

### 2. 이슈 분류 및 우선순위 결정

읽은 알림을 다음 순서로 정렬한다:
1. 🔴 Critical — 즉시 수정
2. 🟡 Warning (반복 패턴) — 반복 횟수 많은 순
3. 🟡 Warning (단발) — 참고만

사용자에게 처리 목록을 보여주고 확인을 받는다:
```
처리할 이슈 목록:

🔴 Critical (N건)
  - [이슈명] — 파일명
  ...

🟡 Warning (N건, 반복)
  - [이슈명] N회 반복 — 파일명
  ...

수정을 진행할까요? (Critical만 / 전체 / 취소)
```

### 3. 이슈별 원인 파악

각 이슈에 대해:

1. **알림 파일의 "추정 원인"과 "수정 방향"** 을 먼저 읽는다
2. **관련 소스 파일을 직접 읽어 확인**한다 — 알림의 추정이 틀릴 수 있음
3. **현재 코드 상태를 확인**한다 — 이미 수정됐을 수 있음
4. 수정이 필요한 경우에만 진행한다

#### 이슈 유형별 확인 포인트

**KIS API 오류 (ConnectTimeout, rt_cd 오류)**
- `backend/app/services/kis_*.py` — 타임아웃 설정, 재시도 로직 확인
- `backend/app/services/kis_token.py` — 토큰 만료/갱신 로직 확인
- 네트워크 문제라면 코드 수정 불필요 → 알림에 "네트워크 일시 장애" 표기

**DB 오류 (Connection, asyncpg)**
- `backend/app/db/session.py` — 커넥션 풀 설정 확인
- `docker compose ps` 로 postgres 컨테이너 상태 확인
- 컨테이너 재시작으로 해소됐으면 코드 수정 불필요

**인증 오류 (401 급증, 로그인 실패 반복)**
- `backend/app/api/auth.py` — rate limit 설정 확인
- `backend/app/core/security.py` — 토큰 검증 로직 확인

**스케줄러 오류**
- `backend/app/services/scheduler.py` — `_consecutive_failures` 임계값 확인
- 마지막 실행 시간 확인

**500 Internal Server Error**
- 해당 엔드포인트 핸들러 파일 확인
- 예외 처리 누락 여부 확인

### 4. 코드 수정

수정이 필요한 경우:
1. 관련 파일을 `Read` 로 읽는다
2. `Edit` 으로 수정한다
3. 로컬 검증:
   ```bash
   # Python 파일 수정 시
   cd backend && source venv/bin/activate && ruff check . && pytest -q --tb=short -x 2>&1 | tail -20

   # TypeScript 파일 수정 시
   cd frontend && npx tsc --noEmit
   ```
4. 검증 통과 후 커밋 + push:
   ```bash
   git add <수정된 파일>
   git commit -m "fix: <이슈 내용 요약>"
   git push
   ```

### 5. CI 대기 및 결과 확인

push 후 반드시 CI 결과를 확인한다. **최대 3회 반복 루프:**

```
[반복 시작]

1. PR 또는 push에 연결된 CI 상태 확인:
   gh run list --branch main --limit 1
   gh run view <run_id> --exit-status

2. CI 완료까지 10초 간격으로 폴링 (최대 10분):
   while not done:
     sleep 10
     gh run view <run_id>

3. CI 결과 분기:

   ✅ 통과 → 6단계로 이동

   ❌ 실패 → CI 실패 처리:
     a. 실패 원인 분석:
        gh run view <run_id> --log-failed
     b. 원인 파악 후 코드 재수정
     c. 로컬 검증 재실행
     d. 커밋 + push
     e. [반복 시작]으로 돌아감

   ⏱ 10분 초과 → 타임아웃 처리:
     - 알림 파일에 "CI 타임아웃" 기록
     - 사용자에게 수동 확인 요청
     - 루프 종료

[최대 3회 반복 후에도 CI 실패 시]
  → 알림 파일에 "자동 수정 실패 — 수동 개입 필요" 기록
  → 루프 종료
```

### 6. 알림 파일 업데이트

각 이슈 처리 후 해당 알림 파일에 결과를 추가한다:

```markdown
---

## 처리 결과 — YYYY-MM-DD HH:MM

### [이슈명]
- **상태**: ✅ 수정 완료 / ⚠️ 코드 외 원인 (네트워크 등) / 🔁 모니터링 필요 / ❌ 자동 수정 실패
- **조치 내용**: `파일경로` N번째 줄 수정 — 구체적 설명
- **커밋**: `git commit hash`
- **CI**: ✅ 통과 / ❌ 실패 (N회 시도)
```

파일 상단에 `[resolved]` 또는 `[failed]` 태그를 추가한다:
```markdown
# 로그 알림 — YYYY-MM-DD HH:00 [resolved]
# 로그 알림 — YYYY-MM-DD HH:00 [failed — 수동 개입 필요]
```

### 7. 완료 출력

```
Fix Alerts 완료

처리한 알림 파일: N개
수정된 이슈: N건
  - ✅ [이슈명] — fix: abc1234 — CI ✅ 통과
  - ⚠️ [이슈명] — 코드 외 원인 (네트워크), 수정 없음
  - ❌ [이슈명] — CI 3회 실패, 수동 개입 필요

다음 /log-check 실행 시 해소 여부가 확인됩니다.
```
