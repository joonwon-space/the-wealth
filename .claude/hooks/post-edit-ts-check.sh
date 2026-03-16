#!/bin/bash
# PostToolUse: Run TypeScript check after editing .ts/.tsx files

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [[ "$FILE" != *.ts && "$FILE" != *.tsx ]]; then
  exit 0
fi

PROJECT_ROOT="/Users/joonwon/Documents/GitHub/the-wealth/frontend"

if [ ! -f "$PROJECT_ROOT/tsconfig.json" ]; then
  exit 0
fi

echo "[ts-check] Running TypeScript check..."
cd "$PROJECT_ROOT" && npx tsc --noEmit 2>&1 | head -30
