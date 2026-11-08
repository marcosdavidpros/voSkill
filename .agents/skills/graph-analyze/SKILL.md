---
name: graph-analyze
description: Requirements, acceptance criteria and Definition of Ready (7 checks)
triggers:
  - graph-analyze
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: ANALYZE
phase: ANALYZE
tokens: ~932
phases: [PRD, DESIGN]
---

# graph-analyze

Requirements, acceptance criteria and Definition of Ready (7 checks). Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- PRD already imported
- Before advancing to DESIGN
- Defining requirements for a new epic

## Mandatory Flow

```
agf import-prd → agf node add (requirement/epic/risk) → agf edge add → agf gate analyze → agf phase design
```

## Steps

Comandos `agf` desta fase (ANALYZE):

| Comando | O que faz |
|---------|-----------|
| `agf import-prd <file>` | Import/update the PRD in the graph |
| `agf node add --type requirement|constraint|risk` | Complete requirements/constraints/risks |
| `agf query --type epic` | Inspect the imported structure |
| `agf edge add <from> <to> --type <rel>` | Link dependencies between nodes |
| `agf gate analyze` | Run the Definition of Ready (7 checks) |

## Flow

```
agf import-prd → agf node add (requirement/epic/risk) → agf edge add → agf gate analyze → agf phase design
```

## Exit

- [ ] DoR passes (7/7)
- [ ] No orphan requirements or cycles
- [ ] ≥1 epic + requirement in graph
- [ ] ≥1 constraint and ≥1 risk node
## Workflow

Step 0: Bootstrap Knowledge — agf search / agf memory read for similar projects

Step 1: Understand Scope — problem statement, target users, core features, NFRs, constraints

Step 2: Import PRD — agf import-prd <file> or create PRD manually

Step 3: Structure Requirements — agf node add --type requirement, epic, constraint, risk

Step 4: Create Edges — agf edge add (requirement → epic, epic → milestone, requirement → requirement)

Step 5: Risk & Constraint Analysis — link risks to affected requirements/epics

Step 6: Save Key Decisions — agf memory write <name>

Step 7: Validate — agf gate analyze (DoR: has_requirements, has_ac, no_orphans, no_cycles, has_constraints, has_risks, prd_quality_score ≥ 60)

Step 8: Transition — agf phase design
## Anti-Patterns

- DO NOT start coding during ANALYZE — this phase is requirements only
- DO NOT create task-level nodes yet — that happens in PLAN
- DO NOT skip risk/constraint analysis — they inform DESIGN decisions
- DO NOT ignore the agf CLI next-action hint — it guides the optimal next command
- DO NOT use deprecated forms — use agf node add to create nodes
## Output Format

```
Phase: ANALYZE → DESIGN
PRD: imported (N requirements, M epics, K risks, J constraints)
Gate: prd_quality — score N/100, grade X
Gate: ready — 7/7 checks passed
Knowledge: L docs imported from cross-project learning
Status: Ready to proceed to DESIGN phase
```
## Related Skills

- $graph-prd — `agf skill show graph-prd`
- $graph-design — `agf skill show graph-design`

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
