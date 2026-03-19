# Manual Tasks

Items requiring user action.

---

## AI 브라우저 에이전트 (Milestone 10)
- [x] Playwright MCP 서버 추가 — `.mcp.json` 으로 자동 인식됨
- [x] `.mcp.json` 파일에 Playwright MCP 설정 추가
- [ ] Claude Preview vs Playwright MCP 비교 테스트 및 문서화
- [ ] Vercel agent-browser CLI 설치 (선택)

## Deployment (Milestone 14)
- [ ] Create Vercel account and link to GitHub repo (frontend)
- [ ] Create Railway/Fly.io account for backend deployment
- [ ] Set up production PostgreSQL and Redis instances

## P0 — DB Backup External Storage (Milestone 13-4)
- [ ] Choose cloud storage provider (S3 / GCS / R2) and create bucket
- [ ] Add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BACKUP_S3_BUCKET` (or equivalent) to `backend/.env`
- [ ] Configure backup container env vars and enable S3 upload in backup script
- [ ] Test restore from backup on staging environment

## P0 — Monitoring & APM (Milestone 14-2)
- [ ] Create Sentry account and get DSN for frontend and backend
- [ ] Add `SENTRY_DSN` to `backend/.env` and `NEXT_PUBLIC_SENTRY_DSN` to frontend env
- [ ] Set up UptimeRobot or Betterstack monitors for the API health endpoint
- [ ] Configure alert channels (email / Slack / Telegram) in chosen monitoring tool
- [ ] Verify Sentry is receiving errors after deployment
