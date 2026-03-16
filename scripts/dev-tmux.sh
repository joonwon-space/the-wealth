#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# dev-tmux.sh — Start frontend + backend in a tmux session
#
# Usage:
#   ./scripts/dev-tmux.sh          # auto-detect local IP
#   ./scripts/dev-tmux.sh 192.168.0.52   # specify IP manually
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION="the-wealth"

# Detect local IP (Wi-Fi interface on macOS)
if [[ -n "${1:-}" ]]; then
  LOCAL_IP="$1"
else
  LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  The Wealth — Dev Server (tmux)"
echo "  Local IP: $LOCAL_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Kill existing session if any
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Create new session with backend pane
tmux new-session -d -s "$SESSION" -n "servers" -c "$PROJECT_DIR"

# ── Pane 0: Backend ──
tmux send-keys -t "$SESSION:servers.0" \
  "cd $PROJECT_DIR/backend && source venv/bin/activate && \
CORS_ORIGINS=\"http://localhost:3000,http://${LOCAL_IP}:3000\" \
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" C-m

# ── Pane 1: Frontend ──
tmux split-window -h -t "$SESSION:servers" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:servers.1" \
  "cd $PROJECT_DIR/frontend && \
NEXT_PUBLIC_API_URL=\"http://${LOCAL_IP}:8000\" \
npm run dev -- --hostname 0.0.0.0" C-m

# Select backend pane
tmux select-pane -t "$SESSION:servers.0"

echo ""
echo "  PC browser:   http://localhost:3000"
echo "  Phone:        http://${LOCAL_IP}:3000"
echo "  API:          http://${LOCAL_IP}:8000/docs"
echo ""
echo "  tmux attach:  tmux attach -t $SESSION"
echo "  tmux kill:    tmux kill-session -t $SESSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Attach to session
tmux attach -t "$SESSION"
