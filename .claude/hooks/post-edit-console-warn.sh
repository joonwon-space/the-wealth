#!/bin/bash
# PostToolUse: Warn about console.log in edited TS/JS files

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [[ "$FILE" != *.ts && "$FILE" != *.tsx && "$FILE" != *.js && "$FILE" != *.jsx ]]; then
  exit 0
fi

if [ ! -f "$FILE" ]; then
  exit 0
fi

COUNT=$(grep -c "console\.log" "$FILE" 2>/dev/null || echo 0)
if [ "$COUNT" -gt 0 ]; then
  echo "[console-warn] WARNING: $COUNT console.log statement(s) found in $FILE — remove before committing"
fi
