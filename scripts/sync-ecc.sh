#!/usr/bin/env bash
# sync-ecc.sh — Pull latest everything-claude-code and sync useful agents/commands to this project

set -euo pipefail

ECC_DIR="/Users/joonwon/Documents/GitHub/everything-claude-code"
CLAUDE_DIR="$(cd "$(dirname "$0")/.." && pwd)/.claude"

# Agents and commands to sync (JS/Python project relevant)
AGENTS=(
  refactor-cleaner
  silent-failure-hunter
  performance-optimizer
  build-error-resolver
  code-explorer
  code-simplifier
  typescript-reviewer
  python-reviewer
)

COMMANDS=(
  checkpoint
  save-session
  resume-session
  refactor-clean
  review-pr
  test-coverage
  quality-gate
)

echo "==> Pulling latest everything-claude-code..."
git -C "$ECC_DIR" pull --ff-only

echo ""
echo "==> Syncing agents..."
for agent in "${AGENTS[@]}"; do
  src="$ECC_DIR/agents/$agent.md"
  dst="$CLAUDE_DIR/agents/$agent.md"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "  ✓ agents/$agent.md"
  else
    echo "  ✗ agents/$agent.md (not found in ECC — skipped)"
  fi
done

echo ""
echo "==> Syncing commands..."
for cmd in "${COMMANDS[@]}"; do
  src="$ECC_DIR/commands/$cmd.md"
  dst="$CLAUDE_DIR/commands/$cmd.md"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "  ✓ commands/$cmd.md"
  else
    echo "  ✗ commands/$cmd.md (not found in ECC — skipped)"
  fi
done

echo ""
echo "Done. To add more items, edit AGENTS or COMMANDS arrays in scripts/sync-ecc.sh"
