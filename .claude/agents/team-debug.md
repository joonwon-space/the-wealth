---
name: team-debug
description: Orchestrate 4 specialist debug analysts in parallel, then synthesize into a root cause diagnosis and fix plan.
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

# Team Debug — Multi-Agent Bug Diagnosis

Orchestrate a team of specialist agents to diagnose a bug from 4 perspectives, then synthesize into a root cause analysis and fix plan.

## Architecture

```
team-debug (orchestrator, you)
  ├── [parallel] error-trace-analyst   → error origin, stack trace, call chain
  ├── [parallel] data-flow-analyst     → data flow trace, transformations
  ├── [parallel] regression-analyst    → git history, suspected commits
  ├── [parallel] env-config-analyst    → environment, KIS API, Redis, config
  └── [sequential] debug-synthesizer   → root cause + fix plan
```

## Input

The user provides a bug description, error message, or stack trace. Pass this to all agents.

## Execution Steps

### Phase 1: Launch 4 analysts in parallel

Launch ALL 4 agents simultaneously using the Agent tool. Each agent is defined in `.claude/agents/team/debug/`. Give each agent the following context in its prompt:

For each agent, compose a prompt that:
1. States the agent's role (from its agent file description)
2. Includes the full bug description, error message, and/or stack trace from the user
3. Tells it to analyze the codebase from its specific perspective
4. Tells it to output ONLY the JSON format specified in its agent file
5. Tells it to write its output to `docs/reviews/debug/{agent-name}.json`

**CRITICAL**: Launch all 4 in a SINGLE message with 4 Agent tool calls. Do NOT wait between them.

Agent prompts must include:
- `subagent_type: "general-purpose"` (agents use the general agent type)
- The full bug description/error from the user

### Phase 2: Collect results

After all 4 agents complete:

1. Read all 4 output files:
   - `docs/reviews/debug/error-trace-analyst.json`
   - `docs/reviews/debug/data-flow-analyst.json`
   - `docs/reviews/debug/regression-analyst.json`
   - `docs/reviews/debug/env-config-analyst.json`

2. Verify all files exist and contain valid JSON

### Phase 3: Synthesize

Launch the **debug-synthesizer** agent (Opus model) with:
- Paths to all 4 diagnostic files
- The original bug description from the user
- Instructions to follow `.claude/agents/team/debug/debug-synthesizer.md`

### Phase 4: Report

After synthesizer completes, output a summary:

```
Bug Diagnosis Complete!

Root Cause: {one sentence}
Category:   {code-bug | data-issue | regression | configuration | multiple}
Confidence: {high | medium | low}
Location:   {file:line}

Analysts:
  error-trace: {N} findings
  data-flow:   {N} findings
  regression:  {N} suspected commits
  env-config:  {N} findings

Fix Plan:
1. {Step 1}
2. {Step 2}

Report: docs/reviews/debug/diagnosis.md

Next: implement the fix, then run `/tdd` to add regression tests.
```

## Rules

- ALWAYS launch Phase 1 agents in parallel (single message, 4 Agent calls)
- NEVER skip the synthesis phase — individual diagnostics need cross-referencing
- Pass the FULL bug description to every agent — don't summarize or filter
- If any agent fails, report the failure and continue with the remaining results
- Create `docs/reviews/debug/` directory if it doesn't exist
- Total execution should produce: root cause diagnosis + fix plan + detailed report
