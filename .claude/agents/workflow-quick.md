---
name: workflow-quick
description: Quick maintenance cycle — lightweight task discovery, batch implementation, docs sync. No team agents.
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
---

# Workflow Quick — Fast Maintenance Cycle

Quick cycle for small improvements: discover-tasks → auto-task → update-docs. No team agents, no review.

## Safety Check (MANDATORY FIRST STEP)

Before doing anything, read `docs/plan/tasks.md` and scan for items tagged with or related to:
- `[security]`, `[auth]`, `[money]`, `[transaction]`, `[migration]`
- Any item mentioning: KIS API, 인증, 암호화, 거래, 비밀번호, 토큰, refresh token

**If ANY such items are found:**
1. Print warning: "tasks.md에 보안/금융 관련 항목이 포함되어 있습니다. `/sprint`를 사용해주세요."
2. List the flagged items
3. **STOP immediately** — do NOT proceed with implementation

## Execution

### Phase 1: DISCOVER (lightweight)

Launch the `discover-tasks` agent:

```
Agent(subagent_type="discover-tasks", prompt="Research project state and refresh tasks.md and todo.md...")
```

Wait for completion.

**Re-run safety check** on the updated `docs/plan/tasks.md`. If new security/financial items were discovered, STOP and suggest `/sprint`.

### Phase 2: IMPLEMENT

Launch the `auto-task` agent:

```
Agent(subagent_type="auto-task", prompt="Execute all incomplete tasks in docs/plan/tasks.md...")
```

Wait for completion. Record the branch name, PR number, and completed task count.

### Phase 3: DOCS

Launch the `doc-updater` agent:

```
Agent(subagent_type="doc-updater", prompt="Sync all docs/ with current codebase state...")
```

### Output

Print final summary:

```
Quick Cycle Complete!

Phase 1 — Discover:   N tasks found
Phase 2 — Implement:  K tasks completed
Phase 3 — Docs:       Updated

Next: run `/quick` again or `/sprint` for a full cycle.
```
