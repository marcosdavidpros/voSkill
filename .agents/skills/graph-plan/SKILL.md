---
name: graph-plan
description: Atomic decomposition (≤2h) + sprint + deterministic scaffold
triggers:
  - graph-plan
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: PLAN
phase: PLAN
tokens: ~984
phases: [DESIGN, IMPLEMENT]
---

# graph-plan

Atomic decomposition (≤2h) + sprint + deterministic scaffold. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- DESIGN ready
- Large tasks need atomic subtasks
- Planning sprint scope

## Mandatory Flow

```
agf context <id> → agf decompose / agf node add → agf edge add → agf forecast → agf insights → agf gate plan → agf phase implement
```

## Steps

Comandos `agf` desta fase (PLAN):

| Comando | O que faz |
|---------|-----------|
| `agf context <id>` | Load epic context |
| `agf decompose` | Detect L/XL tasks and suggest atomic subtasks |
| `agf node add --type task` | Create a task manually |
| `agf edge add <from> <to> --type <rel>` | Map dependencies |
| `agf scaffold <name> [--type class|fn|comp]` | Generate deterministic boilerplate (zero AI) |
| `agf forecast` | DORA metrics to calibrate sprint capacity |
| `agf insights` | Validate sprint health |
| `agf gate plan` | Gate PLAN → IMPLEMENT |

## Flow

```
agf context <id> → agf decompose / agf node add → agf edge add → agf forecast → agf insights → agf gate plan → agf phase implement
```

## Exit

- [ ] Tasks ≤2h with testable AC
- [ ] No L/XL task without subtasks
- [ ] Dependencies mapped (no cycles)
- [ ] Sprint assignments exist
## Workflow

Step 1: Load Context — agf context <epic id>, review DESIGN ADRs

Step 2: Decompose — agf decompose (auto: 1 AC = 1 subtask with test type inference) or manual: agf node add --type task/subtask

Step 3: Map Dependencies — agf edge add (task → task, subtask → task, task → epic, task → decision)

Step 4: Plan Sprint — agf decompose (assign by priority, deps, size, risk)

Step 5: Sync Stack Docs — ensure knowledge base has up-to-date docs before IMPLEMENT

Step 6: Review DORA — agf forecast to calibrate velocity and lead time

Step 7: Validate Sprint — agf insights (balanced load, no oversized, deps resolved)

Step 8: Validate Gate — agf gate plan (all epics decomposed, AC present, no cycles, no oversized)

Step 9: Transition — agf phase implement
## Anti-Patterns

- DO NOT write code during PLAN — this phase is planning only
- DO NOT create tasks >2h — use agf decompose or decompose manually
- DO NOT skip acceptance criteria — they guide TDD in IMPLEMENT
- DO NOT ignore dependencies — they determine execution order
- DO NOT plan everything at once — plan 1-2 sprints ahead, refine later
- DO NOT skip stack-docs refresh — avoids executor hallucination in IMPLEMENT
## Output Format

```
Phase: PLAN → IMPLEMENT
Tasks: N tasks, M subtasks created (K via agf decompose)
Sprints: J sprints planned
Dependencies: D edges mapped
DORA: velocity X tasks/day, lead time P85 Yh
Gate: ready — score N/100, grade X
Status: Ready to proceed to IMPLEMENT phase
```
## Related Skills

- $graph-design — `agf skill show graph-design`
- $graph-implement — `agf skill show graph-implement`

## Token Discipline (`--select`)

Every `agf` command prints a **single-line JSON** envelope to stdout
(`{ok,code,data,error,meta}`); logs are NDJSON on stderr. Consume the smallest slice:

- `agf <cmd> --select data.x,data.y` — project only the fields you need (no `jq`; ~80–90% fewer tokens). Always keeps `ok`/`code`/`error`/`meta`; an invalid path falls back to the full envelope (never errors). E.g. `agf next --select data.node.id,data.node.title`.
- `agf <cmd> --profile claude-code|copilot|opencode|minimal` — agent-aware field presets per command (`--select` wins when both are given).
- `agf exec pipe <cmd>` returns the inner `.data`; `agf exec chain "next; check <id>"` runs a sequence — cross-platform, no shell.
- `--pretty` is for humans only. Never wrap `agf` in `agf compress` — its output is already minimal.

## Codex Notes

- In Codex Plan Mode, use this skill for planning only and do not mutate files.
- During implementation, follow the project `AGENTS.md` rules and use `apply_patch` for manual edits.
