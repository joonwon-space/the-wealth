#!/bin/bash
# PreToolUse: Block --no-verify flag to protect git hooks (pre-commit, commit-msg, pre-push)

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Strip quoted strings to avoid false positives from commit messages
STRIPPED=$(echo "$COMMAND" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")

if echo "$STRIPPED" | grep -qE -- '--no-verify'; then
  echo "BLOCKED: --no-verify flag is not allowed." >&2
  echo "Git hooks (pre-commit, commit-msg, pre-push) must not be bypassed." >&2
  echo "Fix the underlying issue instead of skipping hooks." >&2
  exit 2
fi

echo "$INPUT"
exit 0
