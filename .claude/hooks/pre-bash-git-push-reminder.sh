#!/bin/bash
# PreToolUse: Remind to review changes before git push

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

if [[ "$COMMAND" != *"git push"* ]]; then
  echo "$INPUT"
  exit 0
fi

echo "[git-push] Before pushing, ensure:"
echo "  - No console.log or print() debug statements"
echo "  - No hardcoded secrets or KIS API keys"
echo "  - run /code-review if changes are significant"
echo "  - .env files are NOT staged (check .gitignore)"
echo ""

# Pass through (exit 0 = allow)
echo "$INPUT"
exit 0
