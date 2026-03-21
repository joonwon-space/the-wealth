# Manual Tasks

Items requiring user action.

---

## AI 브라우저 에이전트 (Milestone 10)
- [x] Playwright MCP 서버 추가 -- `.mcp.json` 으로 자동 인식됨
- [x] `.mcp.json` 파일에 Playwright MCP 설정 추가
- [ ] Claude Preview vs Playwright MCP 비교 테스트 및 문서화
- [ ] Vercel agent-browser CLI 설치 (선택)

## KIS API Research Required

- [ ] **해외주식 52주 범위 API 확인**: KIS `HHDFS00000300` API가 `w52hgpr`/`w52lwpr` 미반환 시 대체 API(`HHDFS76410000` 등) 찾아서 fallback 구현 -- KIS API 문서에서 overseas 52w high/low 제공 API TR_ID 확인 필요
- [ ] **해외주식 캔들차트**: KIS 해외주식 일봉 API TR_ID 확인 후 `/stocks/{ticker}/chart` 엔드포인트에 해외주식 지원 추가
- [ ] **섹터 배분 ETF 매핑**: ETF 종목(381170 TIGER미국테크, 481190 TIGER미국S&P500 등)에 대한 `sector_map` 확장 -- 실제 기초지수 기반으로 분류 결정 필요

## P0 -- Monitoring & APM (Milestone 14-2)
- [x] Create Sentry account and get DSN for frontend and backend
- [x] Add `SENTRY_DSN` to `backend/.env` and `NEXT_PUBLIC_SENTRY_DSN` to frontend env
- [x] Set up UptimeRobot or Betterstack monitors for the API health endpoint
- [x] Configure alert channels (email / Slack / Telegram) in chosen monitoring tool
- [ ] Verify Sentry is receiving errors after deployment

## P0 -- DB Backup External Storage (Milestone 13-4)
- [x] Choose cloud storage provider (S3 / GCS / R2) and create bucket — Cloudflare R2 선택
- [x] Add `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` to `backend/.env`
- [x] Configure backup container env vars and enable R2 upload in backup script
- [ ] Test restore from backup on staging environment
