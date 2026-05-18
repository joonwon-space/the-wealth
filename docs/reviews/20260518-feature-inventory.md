# Feature Inventory — 2026-05-18

화면별 현재 구현된 기능 전체 인벤토리. `docs/architecture/frontend-guide.md`, 페이지 컴포넌트 구조, 사이드바 네비게이션을 기준으로 추출.

## 분류 가이드

| 분류 | 의미 |
|---|---|
| **KEEP** | 핵심 가치 — 그대로 유지 |
| **IMPROVE** | 유지하되 개선 필요 (UX·성능·버그) |
| **DEFER** | 지금은 안 쓰지만 미래에 필요 — 숨김/비활성 |
| **REMOVE** | 코드·리소스까지 정리 |

각 항목 옆 `분류` 칸에 위 4개 중 하나를 적고, 필요시 `메모`에 한 줄 사유.

---

## A. 인증 / 온보딩

| 화면·기능 | 경로 | 분류 | 메모 |
|---|---|---|---|
| 랜딩 페이지 (인증 사용자는 `/dashboard` 자동 이동) | `/` |  |  |
| 이메일/비번 로그인 | `/login` |  |  |
| `?reauth=1` 강제 재인증 모드 (Safari 쿠키 호환) | `/login?reauth=1` |  |  |
| 회원가입 | `/register` |  |  |
| 신규 유저 온보딩 가이드 | `/onboarding` |  |  |

## B. 시스템

| 화면·기능 | 경로 | 분류 | 메모 |
|---|---|---|---|
| 오프라인 fallback 페이지 | `/offline` |  |  |
| 디자인 시스템 미리보기 (프로덕션 차단, `ALLOW_DESIGN_PREVIEW=1` 시만) | `/dashboard/design-preview` |  |  |

## C. 메인 대시보드 — 네비게이션 (`/dashboard/*` 공통 레이아웃)

| 기능 | 분류 | 메모 |
|---|---|---|
| 사이드바: 대시보드 · 포트폴리오 · 스트림 · 분석 · 비교 · 투자 일지 · 설정 |  |  |
| 모바일 하단 탭 네비 (< 768px) |  |  |
| 라이트/다크 모드 토글 |  |  |
| 로그아웃 버튼 |  |  |
| 내 계정 아바타 / 설정 링크 |  |  |
| 상단 알림 벨 (unread badge, 드롭다운, 마크 읽음, 전체 읽음) |  |  |

## C-1. 메인 대시보드 본문 (`/dashboard`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 총 자산 카드 (종목 + 예수금, KRW) |  |  |
| 종목 평가 / 예수금 분리 표시 |  |  |
| 일일 변동 (전일 대비 ₩/%, 빨강·파랑) |  |  |
| USD/KRW 환율 표시 |  |  |
| 보유 종목 히트맵 (시가총액 비례 크기, 당일 등락률 색상) |  |  |
| 히트맵 전체화면 모드 + 즉시 표시 툴팁 |  |  |
| 보유 종목 테이블 (TanStack Table 정렬, 다중 컬럼) |  |  |
| 52주 범위 프로그레스 바 |  |  |
| 1M sparkline AreaChart |  |  |
| 포트폴리오 목록 위젯 (PortfolioList) |  |  |
| Top Holdings 위젯 (TopHoldingsWidget) |  |  |
| 워치리스트 섹션 (KRX/NYSE/NASDAQ 마켓 태그) |  |  |
| 트리거된 알림 인라인 표시 |  |  |

## D. 포트폴리오 목록 (`/dashboard/portfolios`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 포트폴리오 카드 (평가금액 ₩, P&L 금액·%, 종목 수, 통화) |  |  |
| 한국 컬러 컨벤션 (이익=빨강, 손실=파랑) |  |  |
| 카드 순서 변경 (drag 핸들) |  |  |
| 카드 이름 인라인 편집 |  |  |
| 카드 삭제 |  |  |
| 새 포트폴리오 추가 |  |  |
| 모바일 카드 뷰 / 데스크탑 그리드 뷰 |  |  |

## E. 포트폴리오 상세 (`/dashboard/portfolios/[id]`)

### E-1. 보유 종목 (HoldingsSection)

| 기능 | 분류 | 메모 |
|---|---|---|
| 종목 행 (수량, 평단가, 현재가, 손익 KRW, 평가금액 KRW) |  |  |
| 매수/매도 버튼 → OrderDialog 호출 |  |  |
| CSV 내보내기 |  |  |
| 종목 추가 |  |  |
| 종목 클릭 → 종목 상세 |  |  |

### E-2. 거래 내역 (TransactionSection)

| 기능 | 분류 | 메모 |
|---|---|---|
| 거래 리스트 + 탭 (전체/매수/매도/배당 등) |  |  |
| 거래 추가 |  |  |
| 거래 수정 (메모·태그·display_order 포함) |  |  |
| 거래 삭제 (soft-delete) |  |  |
| 거래 CSV 내보내기 |  |  |

### E-3. 분석 (AnalysisSection)

| 기능 | 분류 | 메모 |
|---|---|---|
| 평가금액 추이 시계열 차트 |  |  |
| 벤치마크 비교 카드 (vs KOSPI200 / S&P500, delta %) |  |  |
| FX 손익 Top-5 표 (해외 종목 환차손익) |  |  |

### E-4. 보조

| 기능 | 분류 | 메모 |
|---|---|---|
| 예수금 / 사용 가능 / 체결 대기 표시 (pending 차감 반영) |  |  |
| 미체결 주문 패널 (PendingOrdersPanel) + 취소 |  |  |
| 체결 자동 감지 토스트 |  |  |

## F. 종목 검색·상세

### F-1. `/dashboard/stocks` (랜딩)

| 기능 | 분류 | 메모 |
|---|---|---|
| 검색 진입 버튼 (Cmd+K 다이얼로그) |  |  |
| 관심종목 카드 그리드 |  |  |

### F-2. `/dashboard/stocks/[ticker]` (종목 상세)

| 기능 | 분류 | 메모 |
|---|---|---|
| 종목 헤더 (이름, 시장, 현재가, 등락) |  |  |
| 캔들스틱 차트 (1M / 3M / 6M / 1Y / 3Y, ETag 캐싱) |  |  |
| 시가총액 / PER / 거래소 메타 |  |  |
| 52주 범위 프로그레스 바 |  |  |
| 워치리스트 추가/제거 토글 |  |  |
| 매수/매도 다이얼로그 트리거 (전역 CustomEvent) |  |  |

## G. 분석 (`/dashboard/analytics`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 총 자산 / 투자 원금 / 총 손익 카드 |  |  |
| CAGR / MDD / 샤프 비율 지표 카드 + ⓘ 툴팁 |  |  |
| 기간 필터 (1W / 1M / 3M / 6M / 1Y / ALL) |  |  |
| 포트폴리오 가치 추이 차트 |  |  |
| 월별 수익률 히트맵 (ticker-weighted MoM) |  |  |
| 섹터 분포 차트 (SectorAllocationChart) |  |  |
| 종목별 차트 — 보유 종목 중 선택 |  |  |

## H. 비교 (`/dashboard/compare`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 포트폴리오 간 / 벤치마크 대비 비교 |  |  |

## I. 리밸런스 (`/dashboard/rebalance`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 섹터 목표 비중 편집기 |  |  |
| 현재 vs 목표 비중 표시 |  |  |
| 추천 매수/매도 주문 리스트 |  |  |

## J. 스트림 (`/dashboard/stream`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 알림·체결·배당·리밸런스·루틴 이벤트 통합 타임라인 |  |  |
| 이벤트 타입 필터링 |  |  |

## K. 투자 일지 (`/dashboard/journal`)

| 기능 | 분류 | 메모 |
|---|---|---|
| 전체 포트폴리오 거래 메모 통합 뷰 |  |  |
| 일자별 정렬 |  |  |

## L. 설정 (`/dashboard/settings`)

### L-1. AccountSection

| 기능 | 분류 | 메모 |
|---|---|---|
| 이메일 변경 |  |  |
| 비밀번호 변경 |  |  |
| 계정 탈퇴 |  |  |

### L-2. KisCredentialsSection

| 기능 | 분류 | 메모 |
|---|---|---|
| KIS 계좌 등록 (label, account_no, prdt_cd, app_key, app_secret, 모의투자, account_type) |  |  |
| 계좌 정보 수정 (label / 모의투자 / account_type) |  |  |
| 계좌 삭제 |  |  |
| 연결 테스트 |  |  |
| 연금저축(prdt_cd=22) account_type 자동 추론 validator |  |  |

### L-3. PushNotificationsSection

| 기능 | 분류 | 메모 |
|---|---|---|
| Web Push 구독/해제 (VAPID) |  |  |
| 권한 상태 표시 |  |  |
| iOS A2HS 안내 |  |  |

### L-4. ActiveSessionsSection

| 기능 | 분류 | 메모 |
|---|---|---|
| 활성 세션 조회 |  |  |
| 다른 세션 개별 로그아웃 |  |  |
| 전체 세션 로그아웃 |  |  |

### L-5. SecurityLogsSection

| 기능 | 분류 | 메모 |
|---|---|---|
| 보안 감사 로그 (로그인 시도, KIS 자격증명 변경 등) |  |  |
| 탭 가로 스크롤 + 시각 힌트 (모바일) |  |  |

## M. 모든 화면 공통 / 글로벌 기능

| 기능 | 분류 | 메모 |
|---|---|---|
| Cmd+K 글로벌 종목 검색 (한글 초성 지원) |  |  |
| Cmd+? 단축키 도움말 모달 |  |  |
| 알림 벨 — 실시간 unread badge / 마크 읽음 / 전체 읽음 |  |  |
| 매수/매도 다이얼로그 (전역 CustomEvent로 어디서나 호출) |  |  |
| 라이트/다크 모드 (system / manual, next-themes) |  |  |
| SSE 실시간 가격 스트림 (장중 KST 09:00–15:30, 30초 주기, 자동 재연결) |  |  |
| TanStack Query persist (localStorage 24h, 오프라인 시 read-only) |  |  |
| PWA 설치 배너 (Android/Chrome — beforeinstallprompt) |  |  |
| iOS 설치 가이드 모달 (3-step 공유 → 홈 화면에 추가) |  |  |
| Pull-to-refresh (모바일, 대시보드 레이아웃) |  |  |
| 햅틱 피드백 (`navigator.vibrate`) |  |  |
| Web Push 알림 (백그라운드, SW push handler) |  |  |
| Service Worker 업데이트 토스트 (새 버전 감지 → 새로고침 CTA) |  |  |
| 앱 스플래시 (standalone 모드 300ms 로고 페이드인) |  |  |
| AppShell ErrorBoundary (Sentry captureException) |  |  |
| 위젯 단위 ErrorFallback (WidgetErrorFallback) |  |  |

---

## 사용 방법

1. 각 표의 `분류` 열에 KEEP / IMPROVE / DEFER / REMOVE 중 하나를 적습니다.
2. 필요시 `메모` 열에 사유나 우선순위를 한 줄로 적습니다.
3. 작성을 마치면 이 파일을 기반으로:
   - **REMOVE** → 코드/리소스 정리 PR
   - **IMPROVE** → `docs/plan/todo.md` 항목 추가
   - **DEFER** → feature flag·환경변수 게이트로 숨김
   - **KEEP** → 그대로 유지 (액션 없음)

기준점: 본 문서 작성일 2026-05-18 시점의 main 브랜치 코드 (commit `0775d24`).
