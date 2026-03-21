#!/usr/bin/env bash
# Daily PostgreSQL backup script with retention policy.
#
# Environment variables (set in docker-compose or .env):
#   POSTGRES_HOST     — default: postgres
#   POSTGRES_PORT     — default: 5432
#   POSTGRES_USER     — default: postgres
#   POSTGRES_PASSWORD — required
#   POSTGRES_DB       — default: the_wealth
#   BACKUP_DIR        — default: /backups
#   KEEP_DAILY        — number of daily backups to keep (default: 7)
#   KEEP_WEEKLY       — number of weekly backups to keep (default: 4)
#   KEEP_MONTHLY      — number of monthly backups to keep (default: 3)
#   BACKEND_URL       — backend base URL for status reporting (default: http://backend:8000)
#   INTERNAL_SECRET   — shared secret for /internal/backup-status endpoint
#
# Backup naming convention:
#   daily/YYYY-MM-DD.dump
#   weekly/YYYY-WW.dump   (Sunday)
#   monthly/YYYY-MM.dump  (1st of month)

set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-the_wealth}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
KEEP_MONTHLY="${KEEP_MONTHLY:-3}"
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
INTERNAL_SECRET="${INTERNAL_SECRET:-}"

TODAY=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%u)   # 1=Monday … 7=Sunday
DAY_OF_MONTH=$(date +%-d)
YEAR_WEEK=$(date +%G-%V)
YEAR_MONTH=$(date +%Y-%m)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Send backup status to the backend /internal/backup-status endpoint.
# No-ops silently if INTERNAL_SECRET is empty or curl is unavailable.
report_backup_status() {
    local backup_status="$1"
    local message="$2"

    if [ -z "${INTERNAL_SECRET}" ]; then
        log "INTERNAL_SECRET not set — skipping status report"
        return 0
    fi

    if ! command -v curl >/dev/null 2>&1; then
        log "curl not available — skipping status report"
        return 0
    fi

    local payload
    payload=$(printf '{"status":"%s","message":"%s"}' \
        "${backup_status}" \
        "$(echo "${message}" | sed 's/"/\\"/g')")

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Internal-Secret: ${INTERNAL_SECRET}" \
        --data "${payload}" \
        --max-time 10 \
        "${BACKEND_URL}/api/v1/internal/backup-status" 2>/dev/null || echo "000")

    if [ "${http_code}" = "204" ]; then
        log "Backup status reported: ${backup_status}"
    else
        log "Warning: status report returned HTTP ${http_code} (non-fatal)"
    fi
}

# On unexpected exit (non-zero), report failure before the script terminates.
_EXIT_MESSAGE=""
trap '_exit_code=$?; if [ $_exit_code -ne 0 ]; then report_backup_status "error" "Script exited with code $_exit_code. $_EXIT_MESSAGE"; fi' EXIT

dump_database() {
    local dest="$1"
    local dir
    dir="$(dirname "$dest")"
    mkdir -p "$dir"

    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -Fc \
        "$POSTGRES_DB" \
        > "$dest"

    log "Backup written: $dest ($(du -sh "$dest" | cut -f1))"
}

prune_old_backups() {
    local dir="$1"
    local keep="$2"
    local label="$3"

    if [ ! -d "$dir" ]; then
        return 0
    fi

    local count
    count=$(find "$dir" -maxdepth 1 -name "*.dump" | wc -l)
    local to_delete=$(( count - keep ))

    if [ "$to_delete" -le 0 ]; then
        return 0
    fi

    log "Pruning $to_delete old $label backup(s) from $dir (keeping $keep)"
    # Remove oldest files first
    find "$dir" -maxdepth 1 -name "*.dump" | sort | head -n "$to_delete" | while read -r f; do
        log "  Removing: $f"
        rm -f "$f"
    done
}

# ── Daily backup ─────────────────────────────────────────────────────────────
DAILY_FILE="$BACKUP_DIR/daily/$TODAY.dump"
if [ -f "$DAILY_FILE" ]; then
    log "Daily backup already exists: $DAILY_FILE — skipping"
else
    log "Starting daily backup for $TODAY"
    dump_database "$DAILY_FILE"
fi
prune_old_backups "$BACKUP_DIR/daily" "$KEEP_DAILY" "daily"

# ── Weekly backup (Sunday) ────────────────────────────────────────────────────
if [ "$DAY_OF_WEEK" -eq 7 ]; then
    WEEKLY_FILE="$BACKUP_DIR/weekly/$YEAR_WEEK.dump"
    if [ -f "$WEEKLY_FILE" ]; then
        log "Weekly backup already exists: $WEEKLY_FILE — skipping"
    else
        log "Starting weekly backup for week $YEAR_WEEK"
        dump_database "$WEEKLY_FILE"
    fi
    prune_old_backups "$BACKUP_DIR/weekly" "$KEEP_WEEKLY" "weekly"
fi

# ── Monthly backup (1st of month) ─────────────────────────────────────────────
if [ "$DAY_OF_MONTH" -eq 1 ]; then
    MONTHLY_FILE="$BACKUP_DIR/monthly/$YEAR_MONTH.dump"
    if [ -f "$MONTHLY_FILE" ]; then
        log "Monthly backup already exists: $MONTHLY_FILE — skipping"
    else
        log "Starting monthly backup for $YEAR_MONTH"
        dump_database "$MONTHLY_FILE"
    fi
    prune_old_backups "$BACKUP_DIR/monthly" "$KEEP_MONTHLY" "monthly"
fi

log "Backup run complete."
report_backup_status "success" "Daily backup completed for ${TODAY}"
