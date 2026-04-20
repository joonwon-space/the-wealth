---
description: Pull latest everything-claude-code and sync agents/commands to this project
---

# Sync from everything-claude-code

Run the sync script to pull the latest ECC updates and copy relevant agents/commands into this project.

## Steps

1. Run the sync script:

```bash
bash scripts/sync-ecc.sh
```

2. Report what was updated.

3. If new agents or commands were added, remind the user to update CLAUDE.md agent table if needed.

## Arguments

$ARGUMENTS (optional: `--dry-run` to preview without copying)
