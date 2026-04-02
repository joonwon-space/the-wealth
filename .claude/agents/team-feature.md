---
name: team-feature
description: Orchestrate 4 specialist design agents in parallel, then synthesize into a unified PRD and task list for feature implementation.
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

# Team Feature — Multi-Agent Feature Design

Orchestrate a team of specialist agents to design a new feature from 4 perspectives, then synthesize into a unified PRD and implementation plan.

## Architecture

```
team-feature (orchestrator, you)
  ├── [parallel] product-analyst       → user needs, MVP scope, competitive analysis
  ├── [parallel] ux-designer           → UI design, user flows, accessibility
  ├── [parallel] backend-architect     → API, database, KIS integration
  ├── [parallel] frontend-architect    → components, state, data fetching
  └── [sequential] feature-synthesizer → unified PRD + task list
```

## Input

The user provides a feature description/requirement. Pass this to all agents.

## Execution Steps

### Phase 1: Launch 4 designers in parallel

Launch ALL 4 agents simultaneously using the Agent tool. Each agent is defined in `.claude/agents/team/feature/`. Give each agent the following context in its prompt:

For each agent, compose a prompt that:
1. States the agent's role (from its agent file description)
2. Includes the full feature description/requirement from the user
3. Tells it to read relevant existing code to understand current patterns
4. Tells it to output ONLY the JSON format specified in its agent file
5. Tells it to write its output to `docs/reviews/feature/{agent-name}.json`

**CRITICAL**: Launch all 4 in a SINGLE message with 4 Agent tool calls. Do NOT wait between them.

Agent prompts must include:
- `subagent_type: "general-purpose"` (agents use the general agent type)
- The full feature requirement text from the user

### Phase 2: Collect results

After all 4 agents complete:

1. Read all 4 output files:
   - `docs/reviews/feature/product-analyst.json`
   - `docs/reviews/feature/ux-designer.json`
   - `docs/reviews/feature/backend-architect.json`
   - `docs/reviews/feature/frontend-architect.json`

2. Verify all files exist and contain valid JSON

### Phase 3: Synthesize

Launch the **feature-synthesizer** agent (Opus model) with:
- Paths to all 4 analysis files
- The original feature requirement from the user
- Instructions to follow `.claude/agents/team/feature/feature-synthesizer.md`

### Phase 4: Report

After synthesizer completes, output a summary:

```
Feature Design Complete: {Feature Name}

Phase 1 — Specialist Analysis:
  product:    MVP scope = N items, priority = P{X}
  ux:         N pages, M new components, K reusable
  backend:    N endpoints, M DB changes, K KIS API calls
  frontend:   N routes, M components, K data fetches

Phase 2 — Synthesis:
  PRD:   docs/reviews/feature/prd.md
  Tasks: {count} implementation steps

Suggested implementation order:
1. DB migration + models
2. Backend services + API + tests
3. Frontend components + API integration + tests
4. End-to-end integration

Next: review the PRD, then run `/tdd` to start implementing.
```

## Rules

- ALWAYS launch Phase 1 agents in parallel (single message, 4 Agent calls)
- NEVER skip the synthesis phase — raw designs without integration are not useful
- Pass the FULL feature requirement to every agent — don't summarize or filter
- If any agent fails, report the failure and continue with the remaining results
- Create `docs/reviews/feature/` directory if it doesn't exist
- Total execution should produce: PRD document + task breakdown
