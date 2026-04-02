---
name: workflow-fix
description: Bug fix pipeline orchestrator — chains diagnosis, fix implementation, review, release, and docs.
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

# Workflow Fix — Bug Fix Pipeline

Orchestrate the full bug fix lifecycle: diagnose → fix → review → release → docs.

## Input

The user provides a bug description, error message, or stack trace. If none is provided, ask the user before proceeding.

## Financial App Safety Rules (CRITICAL)

**Sensitive paths** — changes here get EXTRA scrutiny:
- `backend/app/services/kis_*` (KIS API)
- `backend/app/core/security.py` (encryption, auth)
- `backend/app/api/*/auth*` (authentication)
- `backend/app/models/transaction*` (transactions)
- `backend/app/services/*transaction*`, `*balance*`, `*portfolio*` (financial logic)

**Rules:**
- Review is NEVER skipped for bug fixes (financial app)
- If fix touches sensitive paths and review returns REQUEST CHANGES → STOP and escalate to user (do NOT auto-fix)
- Financial calculation bugs are always CRITICAL severity

## Execution

### Phase 1: DIAGNOSE

Launch the `team-debug` agent with the user's bug description:

```
Agent(subagent_type="team-debug", prompt="Diagnose bug: {user's description}...")
```

Wait for completion. Read diagnosis from `docs/reviews/debug/diagnosis.md`.

### Phase 2: IMPLEMENT FIX

1. Extract fix steps from `docs/reviews/debug/diagnosis.md`
2. Convert each fix step to `- [ ] <description>` format
3. Write to `docs/plan/tasks.md`
4. Commit: `docs: add fix tasks from diagnosis`

Launch the `auto-task` agent:

```
Agent(subagent_type="auto-task", prompt="Execute all incomplete tasks in docs/plan/tasks.md...")
```

Wait for completion. Record the branch name and completed task count.

### Phase 3: REVIEW (MANDATORY)

**Check sensitive paths first:**

```bash
git diff --name-only HEAD~N..HEAD  # N = number of fix commits
```

Compare changed files against sensitive path patterns.

Launch the `team-review` agent:

```
Agent(subagent_type="team-review", prompt="Review bug fix changes...")
```

Read the verdict from `docs/reviews/review/summary.md`.

**Decision logic:**
- **APPROVE** → proceed to Phase 4
- **REQUEST CHANGES**:
  - If ANY changed file matches sensitive paths → **STOP immediately**, report to user with full diagnosis + review findings
  - If non-sensitive only → implement fixes, re-run review (max 2 retries)
- **BLOCK** → STOP immediately, report to user

### Phase 4: RELEASE

Launch the `team-release` agent:

```
Agent(subagent_type="team-release", prompt="Validate release readiness after bug fix...")
```

Read the decision from `docs/reviews/release/summary.md`.

**Decision logic:**
- **GO** → proceed to Phase 5
- **CONDITIONAL** → report conditions to user
- **NO-GO** → STOP, report blockers

### Phase 5: DOCS

Launch the `doc-updater` agent:

```
Agent(subagent_type="doc-updater", prompt="Sync all docs/ with current codebase state...")
```

### Output

Print final summary:

```
Bug Fixed: {Bug Title}

Phase 1 — Diagnose:   Root cause: {type} (confidence: {level})
Phase 2 — Fix:        N tasks completed
Phase 3 — Review:     VERDICT (sensitive paths: yes/no)
Phase 4 — Release:    DECISION
Phase 5 — Docs:       Updated

Reports:
- docs/reviews/debug/diagnosis.md
- docs/reviews/review/summary.md
- docs/reviews/release/summary.md

Next: verify the fix in production.
```
