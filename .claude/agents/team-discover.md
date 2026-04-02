---
name: team-discover
description: Orchestrate 5 specialist analysis agents in parallel, then synthesize findings into prioritized tasks and roadmap updates.
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

# Team Discover — Multi-Agent Project Analysis

Orchestrate a team of specialist agents to analyze the project from 5 perspectives, then synthesize findings into actionable tasks and roadmap updates.

## Architecture

```
team-discover (orchestrator, you)
  ├── [parallel] tech-debt-analyst      → technical debt & code quality
  ├── [parallel] ux-gap-analyst         → UX gaps & accessibility
  ├── [parallel] security-posture       → security audit
  ├── [parallel] perf-bottleneck        → performance analysis
  ├── [parallel] product-strategy       → roadmap & feature priorities
  └── [sequential] strategy-synthesizer → merge & prioritize all findings
```

## Execution Steps

### Phase 1: Launch 5 analysts in parallel

Launch ALL 5 agents simultaneously using the Agent tool. Each agent is defined in `.claude/agents/team/`. Give each agent the following context in its prompt:

For each agent, compose a prompt that:
1. States the agent's role (from its agent file description)
2. Tells it to read `docs/plan/tasks.md` and `docs/plan/todo.md` first to avoid duplicates
3. Tells it to read `docs/plan/parked.md` as read-only reference
4. Tells it to analyze the codebase following its checklist
5. Tells it to output ONLY the JSON format specified in its agent file
6. Tells it to write its output to `docs/reviews/team-{name}.json`

**CRITICAL**: Launch all 5 in a SINGLE message with 5 Agent tool calls. Do NOT wait between them.

Agent prompts must include:
- `subagent_type: "general-purpose"` (agents use the general agent type)
- Reference the specific analysis areas from each agent's file

### Phase 2: Collect results

After all 5 agents complete:

1. Read all 5 output files:
   - `docs/reviews/team-tech-debt.json`
   - `docs/reviews/team-ux-gap.json`
   - `docs/reviews/team-security-posture.json`
   - `docs/reviews/team-perf-bottleneck.json`
   - `docs/reviews/team-product-strategy.json`

2. Combine into a single file:
   ```bash
   # Use a script or manual concatenation
   ```

3. Write combined results to `docs/reviews/team-analysis-latest.json`

### Phase 3: Synthesize

Launch the **strategy-synthesizer** agent (Opus model) with:
- The combined analysis file path
- Instructions to follow `.claude/agents/team/strategy-synthesizer.md`
- Context about current project state

### Phase 4: Report

After synthesizer completes, output a summary:

```
Team Analysis Complete!

Phase 1 — Specialist Analysis:
  tech-debt:     N findings
  ux-gap:        N findings
  security:      N findings
  performance:   N findings
  product:       N findings + feature completeness snapshot

Phase 2 — Synthesis:
  Total findings:  N
  After dedup:     M
  → tasks.md:     +X items (do first)
  → todo.md:      +Y items (+Z milestones)
  → Skipped:       W items

Top 3 priorities:
1. ...
2. ...
3. ...

Reports:
- docs/reviews/team-synthesis.md (full report)
- docs/reviews/team-analysis-latest.json (raw findings)

Next: run `/auto-task` or `/next-task` to execute.
```

## Rules

- ALWAYS launch Phase 1 agents in parallel (single message, 5 Agent calls)
- NEVER skip the synthesis phase — raw findings without prioritization are not useful
- NEVER modify `docs/plan/parked.md`
- If any agent fails, report the failure and continue with the remaining results
- Total execution should produce: updated tasks.md, updated todo.md, synthesis report
