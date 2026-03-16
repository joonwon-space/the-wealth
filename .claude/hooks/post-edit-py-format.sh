#!/bin/bash
# PostToolUse: Run ruff lint after editing .py files

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [[ "$FILE" != *.py ]]; then
  exit 0
fi

PROJECT_ROOT="/Users/joonwon/Documents/GitHub/the-wealth/backend"
VENV="$PROJECT_ROOT/venv"

if [ ! -d "$VENV" ]; then
  exit 0
fi

echo "[py-check] Running ruff on $FILE..."
"$VENV/bin/ruff" check "$FILE" 2>&1 | head -20

if grep -q "print(" "$FILE" 2>/dev/null; then
  echo "[py-check] WARNING: print() found in $FILE — use logging module instead"
fi
