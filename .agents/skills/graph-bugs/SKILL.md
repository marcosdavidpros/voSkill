---
name: graph-bugs
description: Bug discovery + structured fix (5-Whys) with regression test
triggers:
  - graph-bugs
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: IMPLEMENT
phase: IMPLEMENT
tokens: ~802
phases: [IMPLEMENT]
---

# graph-bugs

Bug discovery + structured fix (5-Whys) with regression test. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Incorrect behavior observed
- Before implementing the fix
- Investigating a production incident

## Mandatory Flow

```
agf node add --type bug → agf start → [TDD: red repro → green fix] → agf done <id>
```

## Steps

Comandos `agf` desta fase (IMPLEMENT):

| Comando | O que faz |
|---------|-----------|
| `agf node add --type bug` | Record the bug with reproduction AC |
| `agf start` | Pull the bug + context + in_progress |
| `agf check <id>` | Validate the fix (regression test green first) |
| `agf done <id>` | Finalize with the root-cause memory |

## Flow

```
agf node add --type bug → agf start → [TDD: red repro → green fix] → agf done <id>
```

## Exit

- [ ] Regression test green
- [ ] Root-cause documented
- [ ] Bug node marked done with reproduction AC
## Workflow

Step 1: Register Bug — agf node add --type bug (with reproduction AC: Given-When-Then of the bug)

Step 2: Start Bug — agf start (pull bug, load context, mark in_progress)

Step 3: Reproduce — write a test that reproduces the bug (RED)

Step 4: 5-Whys — investigate root-cause (5 levels of "why?")

Step 5: Fix — implement the minimal correction (GREEN)

Step 6: Regression Test — ensure the test passes and breaks no others (REFACTOR)

Step 7: Check — agf check <id> (DoD + TDD adherence)

Step 8: Done — agf done <id> (DoD + root-cause memory + done + next)
## Anti-Patterns

- DO NOT fix without a reproduction test first — always red before green
- DO NOT stop at the symptom — investigate to the 5th why (root-cause)
- DO NOT mark done without documenting root-cause — memory write is mandatory
- DO NOT forget the regression test — the fix may break other scenarios
## Output Format

```
Phase: BUGFIX (IMPLEMENT)
Bug: #N registered and fixed
Reproduction: test created (RED → GREEN)
5-Whys: root-cause identified
Regression: all tests pass
Memory: root-cause documented
Status: Bug fixed and documented
```
## Related Skills

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
