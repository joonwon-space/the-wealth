# 모바일 앱웹(PWA) 고도화 계획

> 작성일: 2026-04-24
> 범위: Native 앱 대신 "앱 같은 웹"을 목표로 한 Next.js 프론트엔드 모바일 고도화
> 목표: 홈 화면 설치, 오프라인 앱셸, 푸시 알림, 제스처, 터치 UX, 성능까지 네이티브 체감 수준으로 끌어올린다

---

## 1. 현재 상태 (Baseline)

| 영역 | 상태 | 파일 |
|------|------|------|
| PWA Manifest | **중복 존재** (`public/manifest.json` 과 `app/manifest.ts`) | `frontend/public/manifest.json`, `frontend/src/app/manifest.ts` |
| 아이콘 | 192/512 PNG + SVG 존재 | `frontend/public/icon-*` |
| Viewport meta | 기본값 (`viewport-fit=cover` 미설정) | `frontend/src/app/layout.tsx` |
| 반응형 분기 | `md:` 브레이크포인트 기준 Sidebar ↔ BottomNav | `frontend/src/components/BottomNav.tsx`, `Sidebar.tsx` |
| Safe area | `env(safe-area-inset-*)` 적용 | `BottomNav.tsx`, `dashboard/layout.tsx` |
| Service Worker | **없음** | — |
| A2HS 프롬프트 | **없음** | — |
| Web Push | **없음** (todo.md 15번 백로그) | — |
| 제스처 (swipe, pull-to-refresh) | **없음** | — |
| 테이블 → 카드 전환 | 부분만 적용 (`HoldingsTable` 등 가로 스크롤 위주) | `HoldingsTable.tsx`, `PerformanceTable.tsx` |
| iOS 스플래시 | 기본값 (공식 이미지 미설정) | — |

## 2. 비목표 (Out of Scope)

- 네이티브 앱 래핑 (Capacitor, React Native WebView 등)
- 백그라운드 포지션 스트리밍 (BLE/GPS 등 네이티브-only 기능)
- 앱 스토어 배포

## 3. 성공 지표

| 지표 | 기준 |
|------|------|
| Lighthouse PWA 점수 | 100 |
| Lighthouse Mobile Performance | ≥ 85 (LCP < 2.5s, CLS < 0.1) |
| iOS Safari / Android Chrome 설치 가능 | ✅ (install banner 노출) |
| 오프라인 진입 시 앱 셸 + 최근 포트폴리오 스냅샷 표시 | ✅ |
| Web Push 도달 (구독 → 가격 알림 수신) | End-to-end 성공 |
| 모바일 터치 타겟 | 최소 44×44px, 탭 지연 없음 |

---

## 4. 단계별 실행 플랜 (5 Phase)

### Phase 1 — 기반 정리 + viewport/metadata 정합화 (0.5일)

**왜 먼저 하나**: manifest 중복이 `next build` 에서 어떤 것이 우선하는지 불분명. 후속 작업이 흔들림.

- [ ] **P1-1**: `public/manifest.json` 삭제 (Next App Router `manifest.ts` 로 단일화)
- [ ] **P1-2**: `app/manifest.ts` 에서 아이콘을 PNG(512/192 maskable + any) 우선으로 정리. `purpose: "any maskable"` 분리
- [ ] **P1-3**: `app/layout.tsx` 에 `generateViewport()` 추가 — `viewport-fit=cover`, `themeColor` (라이트/다크 각각), `initialScale=1`, `maximumScale=5` (a11y: pinch 차단 금지)
- [ ] **P1-4**: `apple-touch-icon` 180×180 추가, iOS splash 이미지 6종 (iPhone 15 Pro/Max, SE 등) — `public/splash/` 하위
- [ ] **P1-5**: `globals.css` 루트에 `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation` (버튼 한정), `overscroll-behavior-y: contain` 지정 검토

**검수**: Chrome DevTools → Application → Manifest 섹션에 중복 경고 없음, "Add to Home Screen" 가능

---

### Phase 2 — Service Worker + 앱셸 오프라인 (1.5일)

**왜 하나**: 앱웹의 핵심. 네트워크 끊김 / 지하철 / 느린 4G 에서도 즉시 페인트.

- [ ] **P2-1**: `@serwist/next` 도입 (Workbox 후속, Next 16 지원). `next-pwa` 는 유지보수 지연으로 제외
  - 대안 고려: `next-pwa` vs `@serwist/next` vs 순수 Workbox — 결정 근거를 PR description에 기록
- [ ] **P2-2**: `app/sw.ts` 작성 — 전략:
  - **Precache**: Next 빌드 산출물 (`_next/static/*`), 아이콘, manifest, offline fallback 페이지
  - **Runtime - NetworkFirst**: `/api/v1/*` (실시간 데이터. fallback: 캐시된 직전 응답 + `X-From-Cache` 헤더)
  - **Runtime - StaleWhileRevalidate**: 차트 라이브러리 청크, 폰트
  - **Runtime - CacheFirst**: 이미지, 아이콘
- [ ] **P2-3**: `app/offline/page.tsx` 오프라인 fallback — 최근 포트폴리오 스냅샷(IndexedDB 캐시) 표시
- [ ] **P2-4**: TanStack Query persister 추가 (`@tanstack/query-sync-storage-persister` + IndexedDB) — 포트폴리오/보유종목 쿼리 스냅샷을 offline 진입 시 읽기 전용으로 표시
- [ ] **P2-5**: SW 업데이트 알림 UX — 새 버전 감지 시 Sonner toast "새 버전이 준비됐어요. 새로고침" 버튼

**검수**: DevTools → Network → Offline 체크 후 대시보드 진입 → 앱셸 + 마지막 스냅샷 표시

**리스크**:
- JWT refresh 흐름과 SW 캐싱 간섭 — `/api/v1/auth/*` 는 절대 캐싱 금지 목록에 명시
- SSE(`/prices/stream`) 는 SW bypass 필요 (streaming 응답 캐싱 불가)

---

### Phase 3 — A2HS 설치 유도 + 앱 셸 UX (0.5일)

- [ ] **P3-1**: `useInstallPrompt` 훅 — `beforeinstallprompt` 이벤트 캐치, 적절한 타이밍(홈 2회 방문 or 포트폴리오 추가 후)에 커스텀 배너 노출
- [ ] **P3-2**: iOS(Safari) 분기 — `beforeinstallprompt` 미지원이므로 "공유 → 홈 화면에 추가" 가이드 다이얼로그
- [ ] **P3-3**: 배너 dismiss 상태 `localStorage` 에 저장, 재노출 쿨다운(30일)
- [ ] **P3-4**: 네이티브 감성 로딩 — 앱 실행 직후 스플래시 애니메이션(300ms, primary 토큰 배경 + 로고 페이드인)

**검수**: 크롬 모바일/데스크탑에서 배너 노출, 수락 시 설치 완료

---

### Phase 4 — 터치 UX + 제스처 (2일)

**왜 하나**: 네이티브 앱과 가장 큰 격차. 사용자가 "웹이네"라고 느끼는 1순위 원인.

- [ ] **P4-1**: 홀딩스 테이블 모바일 카드 뷰 (`md:` 미만) — TanStack Table 데이터를 Card 리스트로 렌더링. 정렬/필터는 상단 bottom-sheet (`@base-ui/react` Dialog)
  - 영향: `HoldingsTable.tsx`, `PerformanceTable.tsx`, `PendingOrdersPanel.tsx`, `TransactionSection.tsx`
- [ ] **P4-2**: **Pull-to-refresh** — 대시보드 메인, 포트폴리오 리스트에만 적용. `react-use-gesture` or custom. 당김 → TanStack Query `invalidateQueries`
- [ ] **P4-3**: **좌우 스와이프 탭 이동** — `/dashboard/portfolios/[id]` 의 보유/개요/거래내역 섹션. `embla-carousel-react` 또는 `framer-motion` 드래그
- [ ] **P4-4**: **바텀시트 주문 다이얼로그** — 모바일에서 `OrderDialog` 를 중앙 모달 대신 하단 슬라이드업 시트로. 데스크탑은 기존 유지 (분기)
- [ ] **P4-5**: **햅틱 피드백** — 주문 체결 토스트, 스와이프 삭제 시 `navigator.vibrate(10)`
- [ ] **P4-6**: 롱프레스 컨텍스트 메뉴 — 포트폴리오 카드 롱프레스 → 이름 변경/삭제/공유
- [ ] **P4-7**: 스크롤 성능 — `overflow-y-auto` 영역에 `-webkit-overflow-scrolling: touch`, 가상화(TanStack Virtual) 필요 구간 식별

**검수**: 실제 모바일 기기 또는 Chrome DevTools Device Mode 에서 QA 체크리스트 통과

---

### Phase 5 — Web Push 알림 (2일)

**왜 하나**: `docs/plan/todo.md` 15번 백로그, 앱웹의 killer feature. 가격 알림, 체결 알림.

- [ ] **P5-1**: 백엔드 VAPID 키 생성/보관 (`.env`), `web-push` Python 라이브러리 (`pywebpush`) 설치
- [ ] **P5-2**: DB 스키마 — `push_subscriptions` 테이블 (user_id, endpoint, p256dh, auth, user_agent, created_at)
- [ ] **P5-3**: API — `POST /api/v1/push/subscribe`, `DELETE /api/v1/push/subscribe`
- [ ] **P5-4**: 프런트 — `useWebPush` 훅 (`Notification.requestPermission` → `serviceWorker.ready.pushManager.subscribe` → 백엔드 등록)
- [ ] **P5-5**: SW `push` 이벤트 핸들러 — 가격 알림 payload 받아 `showNotification`, 탭 시 해당 종목 페이지로 이동
- [ ] **P5-6**: 알림 트리거 통합 — 기존 가격 알림 (`price_alerts` 서비스)에 push 발송 분기 추가
- [ ] **P5-7**: 설정 UI — `/dashboard/settings` 에 "모바일 푸시 알림" 토글

**검수**: iPhone/Android 실기기에서 가격 알림 수신 확인

**리스크**:
- iOS Safari 는 **PWA 설치 상태**에서만 푸시 허용 (16.4+) — 설치 유도 우선
- VAPID 키 유출 시 알림 스푸핑 가능 — 백엔드 env 외부 노출 방지

---

## 5. 의존성 / 순서

```
Phase 1 ── Phase 2 ── Phase 3 ── Phase 5 (Push는 SW + 설치 의존)
             │
             └── Phase 4 (제스처는 SW와 독립, 병렬 가능)
```

Phase 4 는 Phase 2 와 병렬 진행 가능. Phase 5 는 반드시 Phase 2·3 완료 후.

## 6. 예상 공수 & 우선순위

| Phase | 공수 | 우선순위 | 사용자 체감도 |
|-------|------|----------|---------------|
| P1 기반 정리 | 0.5일 | P0 | 낮음 (기반) |
| P2 SW + 앱셸 | 1.5일 | P0 | **높음** |
| P3 A2HS | 0.5일 | P1 | 중 |
| P4 제스처/터치 | 2일 | P1 | **매우 높음** |
| P5 Web Push | 2일 | P2 | **높음** |
| **합계** | **~6.5일** | | |

추천 MVP 릴리스 = **P1 + P2 + P4 일부(카드 뷰 + 바텀시트)**. 나머지는 후속 스프린트.

## 7. 리스크 & 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| SW 가 JWT refresh flow 간섭 | 로그인 루프 | `/auth/*` 네트워크 전용 + 명시적 bypass |
| SSE 스트리밍 캐싱 | 실시간 가격 꼬임 | `/prices/stream` SW bypass |
| iOS 푸시 제약 | iOS 사용자 알림 미수신 | 설치 유도 + A2HS 배너 iOS 전용 가이드 |
| 오프라인 데이터 stale | 틀린 시세 노출 | 캐시 응답에 `staleAt` 뱃지 표기 |
| 번들 크기 증가 (gesture libs) | 초기 로드 악화 | 동적 import + 모바일에서만 로드 |
| manifest 중복으로 기존 설치 인스턴스 무효화 | 기존 사용자 재설치 필요 | 릴리스 노트에 안내 |

## 8. 검증 체크리스트

- [ ] Lighthouse PWA 100 점
- [ ] Lighthouse Mobile Performance ≥ 85
- [ ] Chrome Android 실기기 설치 → 오프라인 진입 OK
- [ ] iOS Safari 홈 화면 추가 → 스플래시 → standalone 실행 OK
- [ ] 가격 알림 푸시 수신 (iOS 설치 상태 + Android)
- [ ] 바텀시트, pull-to-refresh, 스와이프 제스처 E2E 테스트
- [ ] `docs/runbooks/` 에 SW 배포/롤백, VAPID 키 rotation 런북 추가

## 9. 작업 산출물

- 코드 PR 5개 (Phase 별)
- `docs/architecture/frontend-guide.md` 갱신 (PWA, SW, 오프라인 섹션)
- `docs/architecture/infrastructure.md` 갱신 (VAPID 키, push 엔드포인트)
- `docs/runbooks/mobile-pwa.md` 신규
- `docs/plan/tasks.md` 에 Phase 별 작업 항목 추가

---

## 10. 열린 질문 (합의 필요)

1. **이 플랜 범위로 괜찮은가?** 더 줄이거나 늘릴 구간
2. **릴리스 전략** — 5개 PR 순차 배포 vs Phase 1-2 묶음 + 3-4-5 개별
3. **Web Push 제공자** — 자체 VAPID(비용 0, 관리 직접) vs Firebase FCM(편함, 3rd-party 노출)
4. **기존 `docs/plan/todo.md#19-1 PWA Web Push` 백로그를 이 플랜의 Phase 5로 치환**해도 되는지
5. **제스처 라이브러리** — `@use-gesture/react` vs `framer-motion` drag 단일화 선호도
