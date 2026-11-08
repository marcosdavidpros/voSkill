---
name: graph-review
description: Blast radius, API contracts and graph visualization
triggers:
  - graph-review
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: REVIEW
phase: REVIEW
tokens: ~914
phases: [VALIDATE, HANDOFF]
---

# graph-review

Blast radius, API contracts and graph visualization. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- VALIDATE complete
- Before HANDOFF
- Reviewing code before PR

## Mandatory Flow

```
agf insights (impact) → agf insights (code_sync) → agf export --format mermaid → agf metrics → agf gate review → agf phase HANDOFF
```

## Steps

Comandos `agf` desta fase (REVIEW):

| Comando | O que faz |
|---------|-----------|
| `agf insights` | Blast radius analysis (Code Intelligence) |
| `agf insights` | Code-aware sync (stale refs, missing testFiles, symbol drift) |
| `agf export --format mermaid` | Visualize graph in Mermaid |
| `agf metrics` | Review velocity, quality, complexity |
| `agf gate review` | Gate REVIEW → HANDOFF (harness ≥ 55) |

## Flow

```
agf insights (impact) → agf insights (code_sync) → agf export --format mermaid → agf metrics → agf gate review → agf phase HANDOFF
```

## Exit

- [ ] Blast radius reviewed (Code Intelligence)
- [ ] Code sync clean (no stale refs)
- [ ] Metrics within acceptable ranges
- [ ] Review gate green
## Workflow

Step 1: Blast Radius — agf insights (upstream/downstream dependents per modified module)

Step 2: Code Sync — agf insights (stale sourceRefs, missing testFiles, symbol drift)

Step 3: Visualize — agf export --format mermaid (or --format csv for tabular)

Step 4: Collect Metrics — agf metrics (velocity, AC pass rates, complexity)

Step 5: Code Review — git diff main...HEAD, git log (quality, security, performance, error handling, ADR compliance)

Step 6: Knowledge Quality — agf search to flag stale RAG entries

Step 7: Validate Gate — agf gate review (all tasks validated, blast radius ok, code_sync clean)

Step 8: Transition — agf phase HANDOFF
## Anti-Patterns

- DO NOT skip blast radius with agf insights — manual analysis misses transitive dependencies
- DO NOT ignore code_sync warnings — stale refs cause confusion in future sprints
- DO NOT rubber-stamp reviews — actually read the diffs
- DO NOT skip the ADR compliance check — design decisions exist for a reason
- DO NOT forget to flag stale RAG knowledge — improves retrieval quality for the team
## Output Format

```
Phase: REVIEW → HANDOFF
Blast radius: N modules affected (Code Intelligence)
Code sync: M stale refs, K missing testFiles
Changes: J files modified, L lines changed
Gate: review_ready — score N/100, grade X
Status: Ready to proceed to HANDOFF phase
```
## Related Skills

- $graph-validate — `agf skill show graph-validate`
- $graph-handoff — `agf skill show graph-handoff`

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
