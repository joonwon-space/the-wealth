# Manual Tasks

Items requiring user action.

---

## KIS API Research Required

- [x] **해외주식 52주 범위 API**: `HHDFS76200200` (price-detail) fallback 구현 완료
- [x] **해외주식 캔들차트**: `HHDFS76240000` (dailyprice) TR_ID 확인 후 chart.py에 해외주식 지원 추가
- [x] **섹터 배분 ETF 매핑**: sector_map.py에 국내 ETF 20개 추가 (TIGER/KODEX/ACE)

## P0 -- Monitoring & APM (Milestone 14-2)
- [x] Create Sentry account and get DSN for frontend and backend
- [x] Add `SENTRY_DSN` to `backend/.env` and `NEXT_PUBLIC_SENTRY_DSN` to frontend env
- [x] Set up UptimeRobot or Betterstack monitors for the API health endpoint
- [x] Configure alert channels (email / Slack / Telegram) in chosen monitoring tool
- [x] Verify Sentry is receiving errors after deployment — 백엔드/프론트엔드 모두 수신 확인 (2026-03-21)

## P0 -- DB Backup External Storage (Milestone 13-4)
- [x] Choose cloud storage provider (S3 / GCS / R2) and create bucket — Cloudflare R2 선택
- [x] Add `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` to `backend/.env`
- [x] Configure backup container env vars and enable R2 upload in backup script
- [x] Test restore from backup on staging environment — 2026-03-21 검증 완료 (users 2, portfolios 6, sync_logs 408)

## P3 -- design-preview baseline 스크린샷 생성 (TASK-RD-9 follow-up, 2026-04-29)

`frontend/e2e/design-preview.spec.ts` 는 작성 완료, CI workflow 도 `ALLOW_DESIGN_PREVIEW=1` 환경변수 주입 설정됨. **단, baseline PNG 가 없어** Playwright 첫 실행에서 fail. 1회 수동 baseline 생성이 필요하다. 디자인 토큰/프리미티브 변경 시에도 같은 절차로 갱신.

소요 시간: ~3분 (frontend dev server 부팅 + auth + 스크린샷 생성).

### 사전 준비
- `frontend/.env.local` 에 `E2E_TEST_EMAIL` / `E2E_TEST_PASSWORD` 설정 (이미 본 세션에서 추가됨, qa계정 = `jwon3711@gmail.com`).
- backend dev server 가 띄워져 있어야 한다 (auth + dashboard 데이터 fetch). `cd backend && uvicorn app.main:app --reload`.

### 절차

1. **frontend dev server 기동 (design-preview 허용 모드)**
   ```bash
   cd frontend
   ALLOW_DESIGN_PREVIEW=1 npm run dev
   # → http://localhost:3000
   ```
2. **다른 터미널에서 baseline 생성**
   ```bash
   cd frontend
   npx playwright test design-preview.spec.ts --update-snapshots --project=chromium
   ```
3. **결과 확인**: `frontend/e2e/design-preview.spec.ts-snapshots/` (혹은 `frontend/test-results/...`) 디렉토리에 `design-preview-light-chromium-*.png` 와 `design-preview-dark-chromium-*.png` 2장 생성.
4. **commit**
   ```bash
   git add 'frontend/e2e/design-preview.spec.ts-snapshots/'
   git commit -m "test(e2e): design-preview baseline screenshots"
   git push origin main
   ```

### 검증

- 같은 명령을 `--update-snapshots` 없이 다시 실행하면 PASS 해야 한다 (`npx playwright test design-preview.spec.ts --project=chromium`).
- CI 의 e2e workflow 가 PR에서 자동 실행될 때 baseline 과 비교, 디자인 회귀가 있으면 fail.

### Troubleshooting

- 로그인 실패 → `E2E_TEST_EMAIL` 미설정. `frontend/.env.local` 확인.
- 페이지가 404 → dev server 가 `ALLOW_DESIGN_PREVIEW=1` 없이 실행됨. 환경변수 다시 설정 후 재기동.
- 스크린샷이 비어있음 → backend 가 안 띄워져서 dashboard fetch 가 실패. backend 부팅 로그 확인.

---

## P3 -- Cloudflare Web Analytics 콘솔 노이즈 제거 (TASK-QA-2, 2026-04-29)

CF Web Analytics 자동 주입 beacon (`/beacon.min.js/v8c78...`) 가 path-versioned URL → canonical 로 edge rewrite 되면서 Chrome 의 `strict-dynamic` CSP 가 redirect 로 감지해 `[ERROR] The script resource is behind a redirect, which is disallowed.` 콘솔 경고를 페이지당 26회 출력. 코드 수정 불필요 — Cloudflare dashboard 설정 사안. **기능 영향 없음, 콘솔 노이즈만 발생.**

소요 시간: ~2분.

- [ ] https://dash.cloudflare.com 로그인 → `joonwon.dev` 사이트 선택
- [ ] 좌측 메뉴 → **Analytics & Logs** → **Web Analytics** → 해당 사이트 **Settings (⚙️)**
- [ ] 셋 중 하나 선택:
  - **(권장)** "Automatic Setup" 끄고 **Manual setup** 으로 전환. dashboard 가 보여주는 snippet (`<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token":"..."}'></script>`) 을 알려주면 `frontend/src/app/layout.tsx` 의 `<head>` 에 추가하고 CSP `script-src` (`frontend/src/proxy.ts` line 24-32) 에 `static.cloudflareinsights.com` 명시적 추가하는 작업은 코드 쪽에서 처리.
  - **대안 1**: Web Analytics 자체 비활성화. 분석은 Sentry / Vercel Analytics 로 대체.
  - **대안 2**: 그대로 두기 — 콘솔 경고만 발생, 기능 정상. WONTFIX.
