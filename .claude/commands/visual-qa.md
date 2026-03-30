---
description: Visual QA
---

# Visual QA

AI가 직접 사이트에 접속해 UI 이슈를 탐지하고 수정 제안을 생성한다.

## 사용법

```
/visual-qa                          → 라이브 서버 전체 페이지 검사 (기본)
/visual-qa --local                  → 로컬 dev 서버 전체 페이지 검사
/visual-qa /dashboard/analytics     → 라이브 서버 특정 페이지만
/visual-qa --local /dashboard/analytics  → 로컬 특정 페이지만
```

## 환경 결정

### 기본값: 라이브 서버 (`--live`)

| 항목 | 값 |
|------|-----|
| Base URL | `https://joonwon.dev` |
| 자격증명 | `VISUAL_QA_EMAIL` / `VISUAL_QA_PASSWORD` 환경변수 |
| 코드 수정 | 불가 — 이슈 리포트만 출력 |
| 전제조건 | 없음 (서버가 이미 떠 있음) |

### `--local` 플래그 사용 시

| 항목 | 값 |
|------|-----|
| Base URL | `http://localhost:3000` |
| 자격증명 | `VISUAL_QA_EMAIL` / `VISUAL_QA_PASSWORD` 환경변수 |
| 코드 수정 | 가능 (Next.js 핫리로드 활용) |
| 전제조건 | `npm run dev` (frontend) + `uvicorn` (backend) 실행 중 |

환경변수가 설정되지 않은 경우 실행 전에 이메일/비밀번호를 직접 물어본다.

## 워크플로우

### 0. 자동 로그인

모든 페이지 검사 전에 반드시 먼저 로그인한다.

```
1. browser_navigate("{BASE_URL}/login")
2. 현재 URL 확인 — 이미 /dashboard면 로그인된 상태이므로 3~5 건너뜀
3. 이메일 입력 필드에 VISUAL_QA_EMAIL 입력
4. 비밀번호 입력 필드에 VISUAL_QA_PASSWORD 입력
5. 로그인 버튼 클릭
6. /dashboard로 리다이렉트됐는지 확인
```

로그인 실패 시:
- 스크린샷을 찍고 에러 메시지를 보고한 뒤 중단한다.
- 자격증명이 올바른지 확인을 요청한다. `--local`이면 서버 실행 여부도 확인한다.

### 1. 대상 페이지 결정

인자가 없으면 다음 페이지를 순서대로 검사한다:
- `/dashboard` (대시보드)
- `/dashboard/analytics` (분석)
- `/dashboard/portfolios` (포트폴리오 목록)
- `/dashboard/journal` (투자 일지)
- `/dashboard/settings` (설정)

경로 인자가 있으면 해당 경로만 검사한다. 예: `/visual-qa /dashboard/analytics`

### 2. 뷰포트별 스크린샷 촬영

각 페이지를 세 가지 뷰포트에서 캡처한다:

| 뷰포트 | 너비 | 대상 |
|--------|------|------|
| mobile | 375px | iPhone SE |
| tablet | 768px | iPad |
| desktop | 1280px | 일반 노트북 |

```
browser_navigate → 페이지 이동
browser_resize → 뷰포트 설정
browser_screenshot → 스크린샷 캡처
```

### 3. 라이트/다크 모드 검사

각 뷰포트에서 라이트·다크 모드 양쪽을 촬영한다.
다크모드 전환: 설정 페이지의 테마 토글 클릭 or `prefers-color-scheme` 에뮬레이션.

### 4. 이슈 탐지 체크리스트

스크린샷을 분석해 다음 항목을 검사한다:

**레이아웃**
- [ ] 요소가 화면 밖으로 넘침 (overflow)
- [ ] 텍스트가 잘림 (text truncation 의도치 않음)
- [ ] 요소 겹침 (z-index 문제)
- [ ] 빈 공간 또는 예상 밖의 여백

**색상 & 테마**
- [ ] 다크모드에서 텍스트 색상이 배경과 충분히 대비되는지
- [ ] 한국 증시 컬러 컨벤션 (상승=빨간색 `#e31f26`, 하락=파란색 `#1a56db`) 준수
- [ ] 라이트/다크 모드 전환 시 잔상 없음

**반응형**
- [ ] 모바일에서 터치 타겟이 충분히 큰지 (최소 44×44px)
- [ ] 모바일 하단 네비게이션 바 정상 표시
- [ ] 테이블이 모바일에서 카드 뷰로 전환되는지

**접근성**
- [ ] 버튼/링크에 텍스트 또는 aria-label 있음
- [ ] 포커스 인디케이터 가시적
- [ ] 색상만으로 정보를 전달하지 않음

### 5. 요소 상세 검사

의심스러운 요소는 `browser_get_text` 또는 `browser_snapshot`으로 DOM 구조를 확인한다.

### 6. 이슈 목록 생성 및 사용자 승인 요청

발견된 이슈를 심각도별로 정리한다:

```
## Visual QA 결과 — {페이지} ({뷰포트})

### 🔴 Critical (기능 불가)
- ...

### 🟡 Warning (UX 저하)
- ...

### 🟢 Minor (개선 권장)
- ...
```

사용자에게 확인 후 수정 진행 여부를 묻는다.

### 7. 이슈 처리

**`--local` 모드** — 코드 수정 및 재검증:
1. 관련 소스 파일을 `Read` 도구로 읽는다
2. `Edit` 도구로 수정한다
3. Next.js 핫 리로드 후 동일 뷰포트에서 재촬영
4. 수정 전후 비교 설명

**라이브 모드 (기본)** — 리포트만 출력, 코드 수정 없음:
- 각 이슈에 원인 파일과 수정 방향을 명시한다
- 사용자가 별도로 `/visual-qa --local`을 실행해 수정할 수 있도록 안내한다

## 출력 형식

```
Visual QA 완료

검사 페이지: N개
촬영 스크린샷: N장 (N 뷰포트 × N 테마)
발견된 이슈: Critical N, Warning N, Minor N
수정된 이슈: N개
```
