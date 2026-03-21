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
