---
name: graph-design
description: ADRs, interfaces and architecture decisions (harness gate ≥ 55)
triggers:
  - graph-design
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: DESIGN
phase: DESIGN
tokens: ~950
phases: [ANALYZE, PLAN]
---

# graph-design

ADRs, interfaces and architecture decisions (harness gate ≥ 55). Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- DoR approved
- Technical decisions need recording
- Modifying existing modules

## Mandatory Flow

```
agf context <id> → agf node add (decision) → agf edge add → agf insights → agf gate design → agf phase plan
```

## Steps

Comandos `agf` desta fase (DESIGN):

| Comando | O que faz |
|---------|-----------|
| `agf context <id>` | Load context of epic/requirement |
| `agf insights` | Impact analysis (Code Intelligence) |
| `agf adr create "<decision>"` | Record ADR (Architecture Decision Record) |
| `agf node add --type decision` | Create architectural decision node |
| `agf node add --type constraint` | Model contracts/seams/interfaces |
| `agf edge add <from> <to> --type <rel>` | Link dependencies |
| `agf constitution --check` | Validate against project principles |
| `agf gate design` | Gate DESIGN → PLAN (ADRs + coupling + harness ≥ 55) |

## Flow

```
agf context <id> → agf node add (decision) → agf edge add → agf insights → agf gate design → agf phase plan
```

## Exit

- [ ] ADRs + interfaces in graph
- [ ] Decisions linked to requirements
- [ ] No orphan requirements without design coverage
- [ ] Design gate green
## Workflow

Step 1: Load Context — agf context <epic or requirement id>, review ANALYZE requirements

Step 2: Impact Analysis — agf insights (Code Intelligence) for existing codebases

Step 3: Create ADRs — agf node add --type decision, format: Status/Context/Decision/Consequences

Step 4: Link Decisions — agf edge add (decision → requirement, decision → epic, decision → risk)

Step 5: Interface Design — agf node add --type constraint for contracts between components

Step 6: Save Decisions — agf memory write <name>

Step 7: Validate — agf gate design (ADRs complete, decisions linked, no orphans, contracts defined)

Step 8: Transition — agf phase plan
## Anti-Patterns

- DO NOT create implementation tasks during DESIGN — that is PLAN
- DO NOT write code — design is documentation and decisions only
- DO NOT skip ADRs — undocumented decisions lead to inconsistency
- DO NOT over-design — focus on decisions affecting MVP scope
- DO NOT ignore Code Intelligence in existing codebases — avoids surprises
## Output Format

```
Phase: DESIGN → PLAN
ADRs: N decision nodes created
Contracts: M interface constraints defined
Impact: K existing modules analyzed
Coverage: J/T requirements addressed by decisions
Gate: design_ready — score N/100, grade X
Status: Ready to proceed to PLAN phase
```
## Related Skills

- $graph-analyze — `agf skill show graph-analyze`
- $graph-plan — `agf skill show graph-plan`

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
