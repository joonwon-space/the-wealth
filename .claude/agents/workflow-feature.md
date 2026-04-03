---
name: workflow-feature
description: Feature pipeline orchestrator — chains design, task promotion, implementation, review, release, and docs.
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

# Workflow Feature — Feature Development Pipeline

Orchestrate the full feature lifecycle: design → promote → implement → review → release → docs.

## Input

The user provides a feature description. If no description is provided, ask the user before proceeding.

## Financial App Safety Rules

**Sensitive paths** (require team-review, never skip):
- `backend/app/services/kis_*` (KIS API)
- `backend/app/core/security.py` (encryption, auth)
- `backend/app/api/*/auth*` (authentication)
- `backend/app/models/transaction*` (transactions)
- `backend/app/services/*transaction*`, `*balance*`, `*portfolio*` (financial logic)

If any changes touch sensitive paths and team-review returns REQUEST CHANGES, do NOT auto-fix — stop and report to user.

## Execution

### Phase 1: DESIGN

Launch the `team-feature` agent with the user's feature description:

```
Agent(subagent_type="team-feature", prompt="Design feature: {user's description}...")
```

Wait for completion. Read PRD from `docs/reviews/feature/prd.md`.

### USER GATE: PRD Approval

Present to the user:
- Feature name and scope summary
- Task count and suggested implementation order
- Estimated complexity (S/M/L)
- Any trade-offs or design decisions made

Ask: "이 PRD로 진행할까요? 수정하고 싶은 부분이 있으면 알려주세요."

**Wait for user confirmation before proceeding.**

### Phase 2: PROMOTE TASKS

Extract the task list from `docs/reviews/feature/prd.md` and write to `docs/plan/tasks.md`:

1. Read the PRD's task breakdown section
2. Convert each task to `- [ ] <description>` format
3. Write to `docs/plan/tasks.md` (append or replace based on current content)
4. Commit: `docs: promote feature tasks from PRD — {feature name}`

### Phase 3: IMPLEMENT

Launch the `team-implement` agent (3 workers in parallel via worktree isolation):

```
Agent(subagent_type="team-implement", prompt="Execute all incomplete tasks in docs/plan/tasks.md using parallel workers...")
```

Wait for completion. Record the branch name, PR number, and completed task count.

### Phase 3.5: CI VERIFICATION

Wait for CI to pass after push. Same procedure as workflow-sprint Phase 2.5:

```bash
BACKEND_RUN=$(gh run list --branch main --workflow "Backend CI" --limit 1 --json databaseId --jq '.[0].databaseId')
FRONTEND_RUN=$(gh run list --branch main --workflow "Frontend CI" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$BACKEND_RUN" --exit-status
gh run watch "$FRONTEND_RUN" --exit-status
```

If CI fails → read logs, fix, push, retry (max 3). Only proceed when green.

### Phase 4: REVIEW

Launch the `team-review` agent:

```
Agent(subagent_type="team-review", prompt="Review all changes for feature: {feature name}...")
```

Read the verdict from `docs/reviews/review/summary.md`.

**Decision logic:**
- **APPROVE** → proceed to Phase 5
- **REQUEST CHANGES** → check if changes touch sensitive paths:
  - Sensitive paths touched → STOP, report to user
  - Non-sensitive → implement fixes, re-run review (max 2 retries)
- **BLOCK** → STOP immediately, report to user

### Phase 5: RELEASE

Launch the `team-release` agent:

```
Agent(subagent_type="team-release", prompt="Validate release readiness for feature: {feature name}...")
```

Read the decision from `docs/reviews/release/summary.md`.

**Decision logic:**
- **GO** → proceed to Phase 6
- **CONDITIONAL** → report conditions to user
- **NO-GO** → STOP, report blockers

### Phase 6: DOCS

Launch the `doc-updater` agent:

```
Agent(subagent_type="doc-updater", prompt="Sync all docs/ with current codebase state...")
```

### Output

Print final summary:

```
Feature Shipped: {Feature Name}

Phase 1 — Design:     PRD with N tasks
Phase 2 — Promote:    N tasks → tasks.md
Phase 3 — Implement:  K tasks completed
Phase 4 — Review:     VERDICT
Phase 5 — Release:    DECISION
Phase 6 — Docs:       Updated

Reports:
- docs/reviews/feature/prd.md
- docs/reviews/review/summary.md
- docs/reviews/release/summary.md

Next: run `/sprint` for next iteration.
```
