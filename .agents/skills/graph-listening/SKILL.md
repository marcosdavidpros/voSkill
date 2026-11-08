---
name: graph-listening
description: Feedback, persisted learning and opening the next cycle
triggers:
  - graph-listening
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: LISTENING
phase: LISTENING
tokens: ~820
phases: [DEPLOY, ANALYZE]
---

# graph-listening

Feedback, persisted learning and opening the next cycle. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Post-deploy
- Collecting signals for the next cycle
- Sprint retrospective

## Mandatory Flow

```
agf learning stats → agf insights → agf node add --type feedback → agf import-prd <new>
```

## Steps

Comandos `agf` desta fase (LISTENING):

| Comando | O que faz |
|---------|-----------|
| `agf learning stats` | Per-agent performance and learned routing |
| `agf node add --type feedback` | Capture feedback as a traceable node |
| `agf insights` | Backlog health analysis (aging, distribution) |
| `agf import-prd <new>` | Open the next cycle from feedback |

## Flow

```
agf learning stats → agf insights → agf node add --type feedback → agf import-prd <new>
```

## Exit

- [ ] Post-deploy baseline saved
- [ ] Feedback captured as traceable nodes
- [ ] Next cycle seeded
## Workflow

Step 1: Learning Review — agf learning stats (per-agent performance, learned routing)

Step 2: Backlog Health — agf insights (aging, distribution, health grade)

Step 3: Capture Feedback — agf node add --type feedback (bugs, improvements, learnings)

Step 4: DORA Retrospective — agf forecast (compare pre-deploy vs post-deploy baseline)

Step 5: Knowledge Cleanup — agf search + flag stale entries for prune

Step 6: Seed Next Cycle — agf import-prd <new> (or agf node add for a new epic)
## Anti-Patterns

- DO NOT lose feedback — always capture as traceable nodes
- DO NOT ignore learning metrics — they improve future routing
- DO NOT skip stale-knowledge cleanup — it degrades RAG quality
- DO NOT start a new cycle without a retrospective — learning is mandatory
## Output Format

```
Phase: LISTENING → ANALYZE (next cycle)
Feedback: N nodes captured
Learning: performance by agent, routing insights
Backlog: health grade X, aging Y days
DORA: delta from baseline (pre vs post-deploy)
Knowledge: M stale entries flagged for prune
Next Cycle: seeded with new epic/requirement
Status: Listening complete, ready for next cycle
```
## Related Skills

- $graph-deploy — `agf skill show graph-deploy`
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
