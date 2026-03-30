#!/bin/bash
# log-check-cron.sh
# crontab에서 매시간 실행. 컨테이너 내부 JSON 파일 로그를 읽어 이상 감지 시 Claude로 분석.
#
# crontab 등록:
#   crontab -e
#   0 * * * * /Users/joonwon/Documents/GitHub/the-wealth/scripts/log-check-cron.sh >> /tmp/log-check.log 2>&1

set -euo pipefail

# ── 설정 ──────────────────────────────────────────────────────────────
COMPOSE_DIR="/Users/joonwon/Documents/GitHub/the-wealth"
REPO_DIR="/Users/joonwon/Documents/GitHub/the-wealth"
TEMP_LOG="/tmp/the-wealth-log-$(date +%Y%m%d%H).txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M KST')
# 1시간 전 ISO timestamp (로그 시간 필터용)
ONE_HOUR_AGO=$(date -v-1H '+%Y-%m-%dT%H' 2>/dev/null || date -d '1 hour ago' '+%Y-%m-%dT%H')
# ──────────────────────────────────────────────────────────────────────

echo "[$(date '+%H:%M')] log-check 시작"

cd "$COMPOSE_DIR"

# 1. 컨테이너 내부 JSON 파일 로그 읽기 (항상 JSON 형식, ANSI 코드 없음)
#    최근 1시간 분량만 필터 (ISO timestamp 접두어로 grep)
docker compose exec -T backend cat /var/log/the-wealth/app.log 2>/dev/null \
  | grep "\"${ONE_HOUR_AGO}\|\"$(date '+%Y-%m-%dT%H')" \
  > "$TEMP_LOG" 2>/dev/null || true

# 파일 로그가 비어있으면 docker stdout 로그로 폴백 (ANSI 제거 후 사용)
if [ ! -s "$TEMP_LOG" ]; then
    docker compose logs backend --since 1h --no-log-prefix 2>/dev/null \
      | sed 's/\x1b\[[0-9;]*[mGKHF]//g' \
      > "$TEMP_LOG" 2>/dev/null || true
fi

# 로그가 비어있으면 종료
if [ ! -s "$TEMP_LOG" ]; then
    echo "✅ 이상 없음 — 로그 없음 ($TIMESTAMP)"
    rm -f "$TEMP_LOG"
    exit 0
fi

# 2. bash pre-filter: ERROR/WARNING 카운트 (Claude 호출 전 무료 검사)
#    JSON 파일 로그: "level":"error" / "level":"warning"
#    ANSI 제거된 stdout 로그: error / warning (plain text)
ERROR_COUNT=$(grep -ci '"level":"error"\|"level": "error"\|] error \| error]' "$TEMP_LOG" 2>/dev/null || echo 0)
WARN_COUNT=$(grep -ci '"level":"warning"\|"level": "warning"\|] warning \| warning]' "$TEMP_LOG" 2>/dev/null || echo 0)
HTTP500_COUNT=$(grep -c '"status_code": 500\|HTTP/[0-9.]* 500\| 500 ' "$TEMP_LOG" 2>/dev/null || echo 0)

TOTAL=$((ERROR_COUNT + WARN_COUNT + HTTP500_COUNT))
echo "[$(date '+%H:%M')] ERROR: ${ERROR_COUNT}건, WARNING: ${WARN_COUNT}건, 500: ${HTTP500_COUNT}건"

# 이상 없으면 Claude 호출 없이 종료 (토큰 절약)
if [ "$TOTAL" -eq 0 ]; then
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
