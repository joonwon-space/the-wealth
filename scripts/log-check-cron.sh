#!/bin/bash
# log-check-cron.sh
# Mac 로컬 crontab에서 매시간 실행. 서버 로그를 SSH로 가져와 이상 감지 시 Claude로 분석.
#
# 설정:
#   SERVER        SSH 접속 주소 (예: user@joonwon.dev)
#   COMPOSE_DIR   서버 내 docker-compose.yml 위치
#   REPO_DIR      로컬 레포지토리 경로
#
# crontab 등록:
#   crontab -e
#   0 * * * * /Users/joonwon/Documents/GitHub/the-wealth/scripts/log-check-cron.sh >> /tmp/log-check.log 2>&1

set -euo pipefail

# ── 설정 ──────────────────────────────────────────────────────────────
SERVER="${LOG_CHECK_SERVER:-user@joonwon.dev}"          # SSH 접속 주소
COMPOSE_DIR="${LOG_CHECK_COMPOSE_DIR:-~/the-wealth}"    # 서버 내 프로젝트 경로
REPO_DIR="${LOG_CHECK_REPO_DIR:-/Users/joonwon/Documents/GitHub/the-wealth}"
TEMP_LOG="/tmp/the-wealth-log-$(date +%Y%m%d%H).txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M KST')
# ──────────────────────────────────────────────────────────────────────

echo "[$(date '+%H:%M')] log-check 시작"

# 1. 서버에서 최근 1시간 로그 가져오기
ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER" \
  "cd $COMPOSE_DIR && docker compose logs backend --since 1h --no-log-prefix 2>/dev/null" \
  > "$TEMP_LOG" 2>/dev/null || {
    echo "[ERROR] SSH 접속 실패: $SERVER"
    exit 1
}

# 로그가 비어있으면 종료
if [ ! -s "$TEMP_LOG" ]; then
    echo "✅ 이상 없음 — 로그 없음 ($TIMESTAMP)"
    rm -f "$TEMP_LOG"
    exit 0
fi

# 2. bash pre-filter: ERROR/WARNING 카운트 (Claude 호출 전 무료 검사)
ERROR_COUNT=$(grep -c '"level":"error"\|"level": "error"\| ERROR \|Traceback\|Exception\|500' "$TEMP_LOG" 2>/dev/null || true)
WARN_COUNT=$(grep -c '"level":"warning"\|"level": "warning"\| WARNING ' "$TEMP_LOG" 2>/dev/null || true)

echo "[$(date '+%H:%M')] ERROR: ${ERROR_COUNT}건, WARNING: ${WARN_COUNT}건"

# 이상 없으면 Claude 호출 없이 종료 (토큰 절약)
if [ "${ERROR_COUNT:-0}" -eq 0 ] && [ "${WARN_COUNT:-0}" -eq 0 ]; then
    echo "✅ 이상 없음 ($TIMESTAMP)"
    rm -f "$TEMP_LOG"
    exit 0
fi

# 3. 이상 감지 시 Claude로 상세 분석
echo "[$(date '+%H:%M')] 이상 감지 — Claude 분석 시작"

LOG_CONTENT=$(cat "$TEMP_LOG")

cd "$REPO_DIR"
claude --dangerously-skip-permissions -p "
다음은 the-wealth 서버의 최근 1시간 백엔드 로그입니다.
.claude/commands/log-check.md 의 지시에 따라 분석하고,
이상 징후가 있으면 docs/alerts/ 폴더에 오늘 날짜-시간 파일명으로 저장해주세요.
파일 저장 후 git add + git commit 까지 해주세요.

--- 로그 시작 ---
${LOG_CONTENT}
--- 로그 끝 ---
" 2>&1

echo "[$(date '+%H:%M')] Claude 분석 완료"
rm -f "$TEMP_LOG"
