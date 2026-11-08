---
name: graph-prd
description: Turn a vague idea into a structured PRD (5W2H, JTBD, Pareto, MoSCoW, INVEST, GWT, Risk Matrix) and import into the graph
triggers:
  - graph-prd
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: ANALYZE
phase: ANALYZE
tokens: ~966
phases: [ANALYZE]
---

# graph-prd

Turn a vague idea into a structured PRD (5W2H, JTBD, Pareto, MoSCoW, INVEST, GWT, Risk Matrix) and import into the graph. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Start of a cycle with a vague idea
- Before ANALYZE when no PRD exists
- When you want structured requirements elicitation

## Mandatory Flow

```
5W2H → JTBD → Pareto → MoSCoW → INVEST → GWT → Risk Matrix → PRD.md → agf import-prd --dry-run → agf import-prd
```

## Steps

Comandos `agf` desta fase (ANALYZE):

| Comando | O que faz |
|---------|-----------|
| `agf generate-prd "<idea>"` | Generate PRD.md from a prompt |
| `agf import-prd <file> --dry-run` | Preview import before persisting |
| `agf import-prd <file>` | Import PRD → graph (epic + tasks + edges) |

## Flow

```
5W2H → JTBD → Pareto → MoSCoW → INVEST → GWT → Risk Matrix → PRD.md → agf import-prd --dry-run → agf import-prd
```

## Exit

- [ ] PRD.md generated and validated
- [ ] Dry-run preview approved
- [ ] Epic + requirements in graph
- [ ] Ready for $graph-analyze
## Workflow

Step 1: Vision & Context — apply 5W2H (What, Why, Who, Where, When, How, How Much)

Step 2: Jobs-to-be-Done — extract 2-5 jobs: "When [situation], I want to [motivation], so I can [outcome]"

Step 3: Brainstorm + Pareto 80/20 — rate Value/Effort, top 20% are Pareto winners

Step 4: MoSCoW — Must (P1-2), Should (P3), Could (P4), Won't (excluded)

Step 5: INVEST decomposition — each task: I-N-V-E-S-T validated, size XS-XL

Step 6: Given-When-Then — 2-3 AC per task, testable, with concrete values

Step 7: Risk Matrix — Probability x Impact, mitigation for High/Critical

Step 8: PRD Generation — save to docs/_internal/prd/<name>.md in parser-compatible format

Step 9: Dry-run — agf import-prd --dry-run to validate extraction before persisting

Step 10: Transition — present summary and guide to $graph-analyze
## Anti-Patterns

- DO NOT skip methodology steps — each feeds the next
- DO NOT write code or architecture decisions — that is DESIGN
- DO NOT import without --dry-run first — validate before committing to the graph
- DO NOT use ## headings for tasks — parser maps ## to epics and ###/#### to tasks
- DO NOT omit **Acceptance criteria:** — parser must detect AC
- DO NOT write vague AC like "system works" — use GWT with measurable outcomes
## Output Format

```
Phase: PRD (Phase 0 — Pre-lifecycle)
Methodologies: 5W2H, JTBD, Pareto 80/20, MoSCoW, INVEST, GWT, Risk Matrix
File: docs/_internal/prd/<name>.md
Epics: N defined
Tasks: M with acceptance criteria
Risks: K identified
Constraints: J defined
Dry-run: agf import-prd --dry-run — X nodes extracted
Quality: PRD-quality gate target ≥ 70/100
Next: $graph-analyze
```
## Related Skills

- $graph-analyze — `agf skill show graph-analyze`

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
