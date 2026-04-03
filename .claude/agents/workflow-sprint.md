---
name: workflow-sprint
description: Full sprint cycle orchestrator — chains discover, implement, review, release, and docs phases with user gates.
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

# Workflow Sprint — Full Development Cycle

Orchestrate a complete sprint cycle: discover → implement → review → release → docs.

## Financial App Safety Rules

**Sensitive paths** (require team-review, never skip):
- `backend/app/services/kis_*` (KIS API)
- `backend/app/core/security.py` (encryption, auth)
- `backend/app/api/*/auth*` (authentication)
- `backend/app/models/transaction*` (transactions)
- `backend/app/services/*transaction*`, `*balance*`, `*portfolio*` (financial logic)

If any changes touch sensitive paths and team-review returns REQUEST CHANGES, do NOT auto-fix — stop and report to user.

## Execution

### Phase 1: DISCOVER

Launch the `team-discover` agent:

```
Agent(subagent_type="team-discover", prompt="Run full team-discover analysis...")
```

Wait for completion. Read the synthesis report from `docs/reviews/team-synthesis.md`.

### USER GATE 1: Priority Confirmation

Present to the user:
- Top 3 priorities from the synthesis
- Total task count in `docs/plan/tasks.md`
- Any security-tagged items

Ask: "이 우선순위로 진행할까요? tasks.md를 수정하고 싶으면 알려주세요."

**Wait for user confirmation before proceeding.**

### Phase 2: IMPLEMENT

Launch the `team-implement` agent (3 workers in parallel via worktree isolation):

```
Agent(subagent_type="team-implement", prompt="Execute all incomplete tasks in docs/plan/tasks.md using parallel workers...")
```

Wait for completion. Record the branch name, PR number, and completed task count.

### Phase 2.5: CI VERIFICATION (MANDATORY — never skip)

**This phase is NOT optional. You MUST wait for CI and fix failures before proceeding. Do NOT ask the user whether to check CI — just do it.**

After implement pushes to remote, wait for BOTH CI pipelines:

```bash
# Wait a few seconds for CI to trigger
sleep 5

# Get the latest push's CI run IDs
BACKEND_RUN=$(gh run list --branch main --workflow "Backend CI" --limit 1 --json databaseId --jq '.[0].databaseId')
FRONTEND_RUN=$(gh run list --branch main --workflow "Frontend CI" --limit 1 --json databaseId --jq '.[0].databaseId')

# Wait for both — these commands block until completion
echo "Waiting for Backend CI ($BACKEND_RUN)..."
gh run watch "$BACKEND_RUN" --exit-status

echo "Waiting for Frontend CI ($FRONTEND_RUN)..."
gh run watch "$FRONTEND_RUN" --exit-status
```

**If CI fails (auto-fix loop, no user confirmation needed):**
1. Read the failed run log: `gh run view <RUN_ID> --log-failed`
2. Analyze the failure (lint error, test failure, config issue, dependency CVE)
3. Fix the issue directly — do NOT ask the user, just fix it
4. Commit, push, and wait for CI again
5. Repeat up to 3 times. If still failing after 3 attempts → STOP and report to user

**Common CI failure patterns:**
- Lint errors (unused imports, React Compiler rules) → fix the source file
- Test failures (stale mock paths after refactoring) → update mock `patch()` targets
- CI config errors (invalid CLI flags in `.yml`) → fix the workflow file
- Dependency CVEs (pip-audit) → bump version in `requirements.txt`

**BLOCKING RULE: Do NOT proceed to Phase 3 until ALL CI checks are green. No exceptions.**

### Phase 3: REVIEW

Launch the `team-review` agent:

```
Agent(subagent_type="team-review", prompt="Review all changes from the latest auto-task sprint...")
```

Read the verdict from `docs/reviews/review/summary.md`.

**Decision logic:**
- **APPROVE** → proceed to Phase 4
- **REQUEST CHANGES** → check if changes touch sensitive paths:
  - Sensitive paths touched → STOP, report to user
  - Non-sensitive → implement fixes, re-run review (max 2 retries)
- **BLOCK** → STOP immediately, report to user

### Phase 4: RELEASE

Launch the `team-release` agent:

```
Agent(subagent_type="team-release", prompt="Validate release readiness...")
```

Read the decision from `docs/reviews/release/summary.md`.

**Decision logic:**
- **GO** → proceed to Phase 5
- **CONDITIONAL** → report conditions to user, ask for confirmation
- **NO-GO** → STOP, report blockers to user

### Phase 5: DOCS

Launch the `doc-updater` agent:

```
Agent(subagent_type="doc-updater", prompt="Sync all docs/ with current codebase state...")
```

### Output

Print final summary:

```
Sprint Complete!

Phase 1 — Discover:   N findings → M tasks created
Phase 2 — Implement:  K tasks completed, branch: auto-task/XXXX
Phase 3 — Review:     VERDICT (N issues found, M fixed)
Phase 4 — Release:    DECISION
Phase 5 — Docs:       Updated

Reports:
- docs/reviews/team-synthesis.md
- docs/reviews/review/summary.md
- docs/reviews/release/summary.md

Next: run `/sprint` again for next iteration, or `/discover-tasks` to check what's next.
```
