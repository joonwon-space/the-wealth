---
description: "Agent orchestration: available agents, parallel execution, multi-perspective analysis"
alwaysApply: true
---
# Agent Orchestration

## Available Agents

Located in `~/.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| tdd-guide | Test-driven development | New features, bug fixes |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits |
| build-error-resolver | Fix build errors | When build fails |
| e2e-runner | E2E testing | Critical user flows |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| doc-updater | Documentation | Updating docs |
| **team-discover** | **Multi-agent project analysis** | **Milestone completion, direction planning** |
| **team-feature** | **Multi-agent feature design** | **New feature design, PRD generation** |
| **team-review** | **Multi-agent code review** | **Large PRs, core module changes** |
| **team-release** | **Multi-agent release validation** | **Before deploy, PR merge** |
| **team-debug** | **Multi-agent bug diagnosis** | **Complex bugs, unknown root cause** |
| **team-implement** | **Multi-agent parallel implementation** | **Batch task execution (backend/frontend/infra 병렬)** |

### Team Discover Sub-Agents (`.claude/agents/team/`)

| Agent | Perspective | Model |
|-------|-------------|-------|
| tech-debt-analyst | Code quality, dependencies, type safety | Sonnet |
| ux-gap-analyst | UX gaps, a11y, responsive, error states | Sonnet |
| security-posture-analyst | OWASP, auth, encryption, vulnerabilities | Sonnet |
| perf-bottleneck-analyst | Bundle, API, DB, caching performance | Sonnet |
| product-strategy-analyst | Roadmap, feature gaps, priorities | Sonnet |
| strategy-synthesizer | Merge & prioritize all findings | **Opus** |

### Team Feature Sub-Agents (`.claude/agents/team/feature/`)

| Agent | Perspective | Model |
|-------|-------------|-------|
| product-analyst | User needs, MVP scope, competitive analysis | Sonnet |
| ux-designer | UI structure, user flows, accessibility | Sonnet |
| backend-architect | API, database, KIS integration design | Sonnet |
| frontend-architect | Components, state, data fetching | Sonnet |
| feature-synthesizer | Unified PRD + task list | **Opus** |

### Team Review Sub-Agents (`.claude/agents/team/review/`)

| Agent | Perspective | Model |
|-------|-------------|-------|
| correctness-reviewer | Logic errors, edge cases, data integrity | Sonnet |
| security-reviewer | Vulnerabilities, auth, injection | Sonnet |
| performance-reviewer | N+1, re-renders, memory leaks | Sonnet |
| maintainability-reviewer | Readability, conventions, architecture | Sonnet |
| review-synthesizer | Unified verdict + prioritized fixes | **Opus** |

### Team Release Sub-Agents (`.claude/agents/team/release/`)

| Agent | Perspective | Model |
|-------|-------------|-------|
| build-validator | Build success, lint, bundle size | Sonnet |
| test-runner | Test suite, coverage analysis | Sonnet |
| migration-checker | Alembic safety, reversibility | Sonnet |
| api-contract-checker | Breaking changes, contract consistency | Sonnet |
| release-synthesizer | Go/no-go decision + release notes | **Opus** |

### Team Debug Sub-Agents (`.claude/agents/team/debug/`)

| Agent | Perspective | Model |
|-------|-------------|-------|
| error-trace-analyst | Error origin, stack trace, call chain | Sonnet |
| data-flow-analyst | Data flow trace, transformations | Sonnet |
| regression-analyst | Git history, suspected commits | Sonnet |
| env-config-analyst | Environment, KIS API, Redis, config | Sonnet |
| debug-synthesizer | Root cause + fix plan | **Opus** |

### Team Implement Sub-Agents (`.claude/agents/team/implement/`)

| Agent | Role | Model |
|-------|------|-------|
| backend-worker | Python backend tasks (API, services, schemas) | Sonnet |
| frontend-worker | TypeScript frontend tasks (pages, components, hooks) | Sonnet |
| infra-worker | Dependencies, config, security, cross-cutting | Sonnet |
| implement-synthesizer | Merge worktrees, resolve conflicts, verify build | **Opus** |

### Workflow Orchestrators (`.claude/agents/workflow-*.md`)

| Agent | Chains | User Gates |
|-------|--------|------------|
| workflow-sprint | discover → implement → review → release → docs | 2 (priorities, deploy) |
| workflow-feature | design → implement → review → release → docs | 1 (PRD approval) |
| workflow-fix | diagnose → fix → review → release → docs | 0 (auto, stops on block) |
| workflow-quick | discover-tasks → auto-task → docs | 0 (refuses sensitive work) |

## Immediate Agent Usage

No user prompt needed:
1. Full development iteration - Use **/sprint** command
2. User describes a new feature - Use **/feature** command
3. Bug report received - Use **/fix** command
4. Quick maintenance/cleanup - Use **/quick** command
5. Complex feature requests - Use **planner** agent
6. Code just written/modified - Use **code-reviewer** agent
7. Bug fix or new feature - Use **tdd-guide** agent
8. Architectural decision - Use **architect** agent
9. Milestone completed, need next direction - Use **team-discover** agent
10. New feature design needed - Use **team-feature** agent
11. Large code changes to review - Use **team-review** agent
12. Before deployment - Use **team-release** agent
13. Complex bug with unknown cause - Use **team-debug** agent
14. Batch implement tasks in parallel - Use **team-implement** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
