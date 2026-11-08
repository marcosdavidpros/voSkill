---
name: graph-quality
description: Refactoring audit (SOLID/DRY/McCabe) + token economy
triggers:
  - graph-quality
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: REVIEW
phase: REVIEW
tokens: ~740
phases: [REVIEW, VALIDATE]
---

# graph-quality

Refactoring audit (SOLID/DRY/McCabe) + token economy. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Code smells or accumulated debt
- Before closing REVIEW
- During VALIDATE for gating

## Mandatory Flow

```
agf harness --violations → agf quality → agf insights
```

## Steps

Comandos `agf` desta fase (REVIEW):

| Comando | O que faz |
|---------|-----------|
| `agf quality` | Gate 95/95 (tests + logs) |
| `agf harness --violations` | List violations by weak dimension |
| `agf compress discover` | Find output-compression opportunities (token cut) |
| `agf insights` | Complexity and duplication (McCabe, DRY) |

## Flow

```
agf harness --violations → agf quality → agf insights
```

## Exit

- [ ] No new violations
- [ ] Weak dimensions addressed
- [ ] Quality gate 95/95 pass
## Workflow

Step 1: Scan Violations — agf harness --violations (missing types, empty catches, console.log, etc.)

Step 2: Quality Gate — agf quality (95/95: tests + logs over src/)

Step 3: Complexity Analysis — agf insights (McCabe, duplication, naming)

Step 4: Token Economy — agf compress discover (token-cut opportunities)

Step 5: Address Issues — prioritize by impact on harness score

Step 6: Re-scan — agf harness to confirm no regression
## Anti-Patterns

- DO NOT ignore harness violations — they degrade agent readiness
- DO NOT refactor without tests — always keep a green suite
- DO NOT optimize prematurely — focus on dimensions <70 first
## Output Format

```
Phase: QUALITY (REVIEW parallel)
Violations: N found, M addressed
Quality Gate: 95/95 — pass/fail
Complexity: McCabe avg X, duplication Y%
Token Economy: Z opportunities discovered
Harness: score X (no regression)
Status: Quality gate passed
```
## Related Skills

- $graph-review — `agf skill show graph-review`
- $graph-validate — `agf skill show graph-validate`

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
