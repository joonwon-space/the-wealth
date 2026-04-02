---
name: team-review
description: Orchestrate 4 specialist code reviewers in parallel, then synthesize into a unified review verdict with prioritized fixes.
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

# Team Review — Multi-Agent Code Review

Orchestrate a team of specialist reviewers to analyze code changes from 4 perspectives, then synthesize into a unified review verdict.

## Architecture

```
team-review (orchestrator, you)
  ├── [parallel] correctness-reviewer     → logic errors, edge cases, bugs
  ├── [parallel] security-reviewer        → vulnerabilities, auth, injection
  ├── [parallel] performance-reviewer     → N+1, rendering, memory leaks
  ├── [parallel] maintainability-reviewer → readability, conventions, architecture
  └── [sequential] review-synthesizer     → unified verdict + prioritized fixes
```

## Input

Determine what to review:
1. If the user specifies files → review those files
2. If recent uncommitted changes exist → review `git diff` and `git diff --staged`
3. If on a feature branch → review `git diff main...HEAD`

## Execution Steps

### Phase 0: Determine review scope

Run `git status` and `git diff --stat` to understand what changed. Collect:
- List of changed files
- The diff content (or summary for large diffs)

### Phase 1: Launch 4 reviewers in parallel

Launch ALL 4 agents simultaneously using the Agent tool. Each agent is defined in `.claude/agents/team/review/`. Give each agent the following context in its prompt:

For each agent, compose a prompt that:
1. States the agent's role (from its agent file description)
2. Lists all changed files to review
3. Tells it to read each changed file and analyze the changes
4. Tells it to output ONLY the JSON format specified in its agent file
5. Tells it to write its output to `docs/reviews/review/{agent-name}.json`

**CRITICAL**: Launch all 4 in a SINGLE message with 4 Agent tool calls. Do NOT wait between them.

Agent prompts must include:
- `subagent_type: "general-purpose"` (agents use the general agent type)
- The full list of changed files and what kind of changes (new, modified, deleted)

### Phase 2: Collect results

After all 4 agents complete:

1. Read all 4 output files:
   - `docs/reviews/review/correctness-reviewer.json`
   - `docs/reviews/review/security-reviewer.json`
   - `docs/reviews/review/performance-reviewer.json`
   - `docs/reviews/review/maintainability-reviewer.json`

2. Verify all files exist and contain valid JSON

### Phase 3: Synthesize

Launch the **review-synthesizer** agent (Opus model) with:
- Paths to all 4 review files
- Instructions to follow `.claude/agents/team/review/review-synthesizer.md`

### Phase 4: Report

After synthesizer completes, output a summary:

```
Code Review Complete!

Verdict: {APPROVE | REQUEST CHANGES | BLOCK}

Reviewers:
  correctness:     {verdict} — {N} findings
  security:        {verdict} — {N} findings
  performance:     {verdict} — {N} findings
  maintainability: {verdict} — {N} findings

Must Fix:    {N} items
Should Fix:  {N} items
Consider:    {N} items

Report: docs/reviews/review/summary.md
```

## Rules

- ALWAYS launch Phase 1 agents in parallel (single message, 4 Agent calls)
- NEVER skip the synthesis phase — unmerged reviews are confusing
- If any agent fails, report the failure and continue with the remaining results
- Create `docs/reviews/review/` directory if it doesn't exist
- For large diffs (>1000 lines), tell agents to focus on the most impactful changes
