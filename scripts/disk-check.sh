#!/usr/bin/env bash
# disk-check.sh — Docker 볼륨 디스크 사용량 모니터링
#
# 용도: cron 또는 Docker healthcheck에서 호출
#   * 사용률 80% 미만 → INFO JSON 로그, exit 0
#   * 사용률 80% 이상 → CRITICAL JSON 로그, exit 1
#
# 환경 변수:
#   DISK_THRESHOLD  — 경고 임계값 (%, 기본 80)
#   CHECK_PATHS     — 공백 구분 경로 목록 (기본: / /var/lib/docker /tmp)

set -euo pipefail

THRESHOLD="${DISK_THRESHOLD:-80}"
PATHS="${CHECK_PATHS:-/ /var/lib/docker /tmp}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

log_json() {
    local level="$1"
    local message="$2"
    local path="$3"
    local used_pct="$4"
    local avail="$5"

    printf '{"timestamp":"%s","level":"%s","event":"disk_check","path":"%s","used_pct":%s,"avail_human":"%s","threshold":%s,"message":"%s"}\n' \
        "$TIMESTAMP" "$level" "$path" "$used_pct" "$avail" "$THRESHOLD" "$message"
}

has_critical=0

for CHECK_PATH in $PATHS; do
    # 경로가 존재하지 않으면 건너뜀
    if ! mountpoint -q "$CHECK_PATH" 2>/dev/null && [ ! -d "$CHECK_PATH" ]; then
        continue
    fi

    # df 결과 파싱 (macOS / Linux 호환)
    df_out="$(df -k "$CHECK_PATH" 2>/dev/null | tail -1)" || continue
    used_pct="$(echo "$df_out" | awk '{gsub(/%/, "", $5); print $5}')"
    avail_kb="$(echo "$df_out" | awk '{print $4}')"

    # avail 사람이 읽기 좋게 변환 (MB/GB)
    if [ "$avail_kb" -ge 1048576 ]; then
        avail_human="$(awk "BEGIN {printf \"%.1fGB\", $avail_kb/1048576}")"
    else
        avail_human="$(awk "BEGIN {printf \"%.0fMB\", $avail_kb/1024}")"
    fi

    if [ -z "$used_pct" ] || ! [ "$used_pct" -eq "$used_pct" ] 2>/dev/null; then
        continue
    fi

    if [ "$used_pct" -ge "$THRESHOLD" ]; then
        log_json "CRITICAL" "Disk usage ${used_pct}% exceeds threshold ${THRESHOLD}%" \
            "$CHECK_PATH" "$used_pct" "$avail_human"
        has_critical=1
    else
        log_json "INFO" "Disk usage ${used_pct}% is within threshold ${THRESHOLD}%" \
            "$CHECK_PATH" "$used_pct" "$avail_human"
    fi
done

exit "$has_critical"
