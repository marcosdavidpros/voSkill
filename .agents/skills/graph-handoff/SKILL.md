---
name: graph-handoff
description: PR, memory capture and graph snapshot
triggers:
  - graph-handoff
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: HANDOFF
phase: HANDOFF
tokens: ~877
phases: [REVIEW, DEPLOY]
---

# graph-handoff

PR, memory capture and graph snapshot. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- REVIEW approved
- Delivery/PR imminent
- Finalizing sprint

## Mandatory Flow

```
agf memory write <name> → agf snapshot create → agf export → [create PR] → agf gate handoff → agf phase DEPLOY
```

## Steps

Comandos `agf` desta fase (HANDOFF):

| Comando | O que faz |
|---------|-----------|
| `agf memory write <name>` | Capture cycle knowledge/decisions |
| `agf snapshot create` | Backup/rollback of the graph |
| `agf export` | Serialize graph for PR description |
| `agf export --format mermaid` | Visual overview for PR |
| `agf gate handoff` | Gate HANDOFF (snapshot + doc_completeness) |

## Flow

```
agf memory write <name> → agf snapshot create → agf export → [create PR] → agf gate handoff → agf phase DEPLOY
```

## Exit

- [ ] Memories saved
- [ ] Snapshot created
- [ ] Knowledge exported
- [ ] PR created (if applicable)
- [ ] Documentation updated
- [ ] handoff_ready ok
## Workflow

Step 1: Capture Decisions — agf memory write <name> (architecture, patterns, performance, integration)

Step 2: Create Snapshot — agf snapshot create (audit trail)

Step 3: Export Deliverables — agf export (summary for PR description)

Step 4: Share Knowledge — agf export (knowledge package for cross-project sharing)

Step 5: Prepare Commit — git status, git diff --staged, git log --oneline -5

Step 6: Create PR — gh pr create (summary, tasks, test results, breaking changes, mermaid graph)

Step 7: Validate Docs — agf gate handoff (CLAUDE.md, ADRs, API docs updated)

Step 8: Validate Gate — agf gate handoff (all tasks done, snapshot, knowledge, memories, PR, docs)

Step 9: Transition — agf phase DEPLOY
## Anti-Patterns

- DO NOT skip agf memory write — decisions lost now are re-discovered expensively later
- DO NOT skip snapshots — they provide an audit trail
- DO NOT create PRs without test results in the body
- DO NOT forget to update CLAUDE.md with new conventions
- DO NOT skip knowledge export — it enables cross-project learning
## Output Format

```
Phase: HANDOFF → DEPLOY
PR: #N (url)
Snapshot: created
Memories: N decisions captured
Knowledge: M docs exported
Gate: handoff_ready — score N/100, grade X
Status: Ready to proceed to DEPLOY phase
```
## Related Skills

- $graph-review — `agf skill show graph-review`
- $graph-deploy — `agf skill show graph-deploy`

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
