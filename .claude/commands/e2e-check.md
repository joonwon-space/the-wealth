---
description: E2E Check
---

# E2E Check

핵심 사용자 플로우를 Playwright MCP로 자동 검증하고 성공/실패 리포트를 생성한다.

> **Read-only 모드 (필수)** — 이 명령은 어떤 데이터도 mutate하지 않는다. 라이브 환경에서 사용자 본인 계정의 데이터를 보호하고, 로컬에서도 일관된 동작을 보장한다.
>
> **금지 동작:**
> - 회원가입 (`POST /auth/register`)
> - 포트폴리오 / 보유 종목 / 거래 생성·수정·삭제 (`POST/PATCH/DELETE /portfolios*`, `/holdings*`, `/transactions*`)
> - 주문 송출 (`POST /orders*`, `PATCH /orders/*/cancel`)
> - 알림 / 워치리스트 / 푸시 구독 등록·수정·삭제
> - 비밀번호 변경, 회원 탈퇴, KIS 계정 등록·수정·삭제
> - 어떤 form submit / "저장" / "추가" / "삭제" / "주문" / "확인" 버튼 클릭
>
> **허용 동작:**
> - GET 요청 (페이지 navigation, 데이터 조회)
> - 검색 다이얼로그 열기/닫기 (검색 자체는 GET-only)
> - 차트 hover, 탭/필터 전환 (UI state만 변경)
> - 로그인 / 로그아웃 (세션 토큰 발급·삭제 — 데이터 변경 없음)
> - 다크모드 토글 (preference만)
> - 다이얼로그 열기 (단, 폼 제출 금지)
>
> **위반 시 즉시 중단**하고 사용자에게 보고한다.

## 사용법

```
/e2e-check [flow]
```

`flow` 생략 시 전체 플로우를 순서대로 실행한다.

| flow 인자 | 검증 내용 (read-only) |
|-----------|----------|
| `auth` | 로그인 → 보호 경로 접근 → 로그아웃 → 보호 경로 차단 확인 |
| `portfolio` | 포트폴리오 목록 조회 → 상세 페이지 렌더 → 보유 종목 테이블 표시 → 거래 내역 표시 |
| `dashboard` | 대시보드 요약 카드 로딩 → 가격 표시 → 알림 배지 |
| `analytics` | 분석 페이지 지표 → 히트맵 → 포트폴리오 추이 |
| `search` | 종목 검색 (국내/해외/초성) → 종목 상세 → 캔들스틱 |

예시:
- `/e2e-check` — 전체 플로우 (read-only)
- `/e2e-check auth` — 인증 플로우만

## 전제조건

- Playwright MCP 활성화 (`.mcp.json` 참조)
- 프론트엔드 dev server: `cd frontend && npm run dev`
- 백엔드 dev server: `cd backend && uvicorn app.main:app --reload`
- **기존 테스트 계정** (read-only이므로 신규 가입 안 함). `frontend/.env.local`의 `E2E_TEST_EMAIL` / `E2E_TEST_PASSWORD` 또는 `backend/.env`의 `VISUAL_QA_EMAIL` / `VISUAL_QA_PASSWORD` 사용.
- 라이브 환경에서 돌리는 경우 사용자 본인 계정의 기존 데이터(포트폴리오 ≥ 1개)가 미리 존재해야 portfolio/dashboard/analytics 플로우가 의미 있는 검증이 됨.

## 플로우 정의 (read-only)

### Flow 1: auth — 인증 (회원가입 제외)

```
1. browser_navigate("http://localhost:3000/login")
2. 이메일/비밀번호 입력 (기존 테스트 계정) → 로그인 버튼 클릭
3. /dashboard 리다이렉트 확인
4. (보호 경로 확인) /dashboard/portfolios 등 추가 navigation
5. 사이드바 → 로그아웃 버튼 클릭
6. /login 리다이렉트 확인
7. 로그아웃 후 /dashboard 직접 접근 → /login 리다이렉트 확인
```

검증 포인트:
- [ ] 기존 계정 로그인 성공 후 대시보드 이동
- [ ] (선택) 잘못된 비밀번호 시 에러 메시지 표시 — **별도 dummy 비밀번호로만**, 본 계정 비밀번호는 절대 잘못 입력하지 않음
- [ ] 로그아웃 후 보호 경로 접근 차단
- [ ] **회원가입 플로우는 실행 금지**

### Flow 2: portfolio — 포트폴리오 read-only 점검

```
1. /dashboard/portfolios 이동
2. 포트폴리오 카드 N개 렌더링 확인
3. 첫 portfolio 카드 클릭 → /dashboard/portfolios/{id} 이동
4. 보유 종목 테이블 행 수, ticker / name / 평가금액 표시 확인
5. "거래 내역" 탭 클릭 → 거래 리스트 표시 확인
6. "분석" 섹션 — portfolio-history 차트, benchmark 카드, FX 카드 렌더 확인
7. (다이얼로그 열기 금지) "포트폴리오 추가", "종목 추가", "거래 추가" 버튼 클릭 금지
```

검증 포인트:
- [ ] 포트폴리오 목록 정상 로딩 (count > 0)
- [ ] 상세 페이지에서 holdings 데이터 정상 표시
- [ ] 거래 내역 탭 전환 시 데이터 표시
- [ ] **mutation 버튼 클릭 금지**

### Flow 3: dashboard — 대시보드

```
1. /dashboard 이동
2. 요약 카드 로딩 완료 확인 (총 평가금액 텍스트 존재)
3. 보유 종목 테이블 렌더링 확인
4. 전일 대비 배지 표시 확인
5. 52주 범위 프로그레스 바 표시 확인
6. 1M sparkline AreaChart SVG 렌더 확인
7. 모바일(375px)에서 카드 뷰 전환 확인 (browser_resize)
```

검증 포인트:
- [ ] 총 평가금액 숫자 형식 (₩ 단위 콤마)
- [ ] 상승/하락 색상 컨벤션 (빨강/파랑)
- [ ] 모바일에서 하단 네비게이션 바 표시
- [ ] SSE 연결 시 가격 업데이트 인디케이터 (구독만, 주문 송출 없음)

### Flow 4: analytics — 분석 페이지

```
1. /dashboard/analytics 이동
2. 성과 지표 카드 (총 수익률, CAGR, MDD, 샤프) 로딩 확인
3. 포트폴리오 가치 추이 차트 렌더링 확인
4. 기간 선택 버튼 (1M/3M/6M/1Y/ALL) 클릭 → 차트 갱신 (UI state, mutation 아님)
5. 월별 수익률 히트맵 렌더링 확인
```

검증 포인트:
- [ ] 스켈레톤 → 실제 데이터 전환
- [ ] 차트 툴팁 표시
- [ ] 기간 변경 시 차트 업데이트

### Flow 5: search — 종목 검색

```
1. Cmd+K 단축키로 검색 다이얼로그 열기
2. "삼성전자" 검색 → 결과 목록 확인
3. 초성 "ㅅ" 검색 → 초성 검색 동작 확인
4. "AAPL" 검색 → 해외 주식 결과 확인
5. 검색 결과 클릭 → 종목 상세 페이지 이동
6. 캔들스틱 차트 렌더링 확인
7. 기간 선택 (1M/3M/6M/1Y) 동작 확인
8. **모바일 viewport에서 buy/sell 버튼이 보이더라도 클릭 금지** (OrderDialog 띄우는 것까진 허용해도 폼 제출 금지)
```

검증 포인트:
- [ ] 검색 다이얼로그 열기/닫기 (Esc)
- [ ] 실시간 검색 결과 업데이트
- [ ] 종목 상세 페이지 펀더멘털 데이터 표시
- [ ] 52주 범위 프로그레스 바
- [ ] **워치리스트 추가 / 주문 제출 금지**

## 오류 처리 및 디버깅

각 단계 실패 시:

1. **스크린샷 캡처** — 현재 화면 상태 저장
2. **콘솔 로그 확인** — `browser_console_messages` 로 JS 에러 확인
3. **네트워크 요청 확인** — API 응답 상태 코드 확인
4. **원인 분류**:
   - 프론트엔드 렌더링 오류 → 컴포넌트 파일 확인
   - API 에러 (4xx/5xx) → 백엔드 로그 확인
   - 인증 오류 → 토큰/쿠키 상태 확인

만약 실수로 mutation 버튼이 클릭됐다면:
- 즉시 중단
- 사용자에게 어떤 데이터가 영향받았는지 보고
- 가능하면 사용자가 직접 롤백할 수 있도록 정보 제공

## 출력 형식

```
## E2E Check 결과 (read-only)

**실행 시각**: YYYY-MM-DD HH:mm
**검증 플로우**: {flow 목록}

| 플로우 | 단계 | 결과 |
|--------|------|------|
| auth | 로그인 | ✅ |
| auth | 보호 경로 navigation | ✅ |
| auth | 로그아웃 | ✅ |
| portfolio | 목록 조회 | ✅ |
| ... | ... | ... |

**요약**: {성공 N} / {전체 N} 단계 통과
**Mutation 시도 횟수**: 0 (반드시 0이어야 함)

### 실패한 단계
{실패 내용 및 원인 상세}
```
