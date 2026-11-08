---
name: graph-implement
description: TDD Red → Green → Refactor, driven by the guardrailed loop
triggers:
  - graph-implement
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: IMPLEMENT
phase: IMPLEMENT
tokens: ~956
phases: [PLAN, VALIDATE, BUGS]
---

# graph-implement

TDD Red → Green → Refactor, driven by the guardrailed loop. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- An unblocked task exists
- WIP=1: the previous is already done
- Executing atomic tasks

## Mandatory Flow

```
agf start → [TDD: red→green→refactor] → agf check <id> → agf done <id>
```

## Steps

Comandos `agf` desta fase (IMPLEMENT):

| Comando | O que faz |
|---------|-----------|
| `agf start` | Pull next task: wake-up + context + mark in_progress |
| `agf context <id>` | Load compact context-pack + node RAG |
| `agf check <id>` | Definition of Done (8 checks) + TDD adherence |
| `agf done <id>` | Finalize: DoD + write memory + learning record + mark done + suggest next |
| `agf autopilot --gate-gaps --heal-on-fail` | Loop autônomo opt-in: pre-gate determinístico de gaps + diagnóstico MAPE-K na falha |
| `agf harness` | Agent-readiness (do not let it regress > 5pts) |

## Flow

```
agf start → [TDD: red→green→refactor] → agf check <id> → agf done <id>
```

## Exit

- [ ] Tests green (npm run test:blast)
- [ ] DoD passes (8 checks)
- [ ] Harness no regression (>5pts)
- [ ] Code committed with descriptive message
## Workflow

Step 1: Pull Task — agf start (pull next, load context, mark in_progress)

Step 2: Read Context — agf context <id> (compact + RAG, interfaces/decisions the task depends on)

Step 3: Red — write a failing test based on the AC (Given-When-Then)

Step 4: Green — implement the minimum to pass the test

Step 5: Refactor — improve code without breaking tests

Step 6: Run Blast — npm run test:blast (<60s, required)

Step 7: Check DoD — agf check <id> (8 checks: AC, quality, blockers, status flow, description, size, testable AC, testFiles)

Step 8: Done — agf done <id> (DoD + memory + learning record + done + next suggestion)

Opt-in (loop autônomo): agf autopilot --gate-gaps (escala se gap required ancorado) · --heal-on-fail (diagnóstico MAPE-K dry-run na falha). Default OFF → loop byte-idêntico.
## Anti-Patterns

- DO NOT implement without a test first — TDD is mandatory
- DO NOT let WIP >1 — finish the current before pulling the next
- DO NOT mark done without running agf check — validation is mandatory
- DO NOT refactor neighbors without AC — additive changes only
- DO NOT skip the blast test — mandatory gate per task
- DO NOT allow harness regression >5pts — quality cannot regress
## Output Format

```
Phase: IMPLEMENT
Tasks: N done, M in_progress
Tests: blast pass <60s
DoD: 8/8 checks pass
Harness: score X (ΔY pts)
Status: Ready for next task or VALIDATE
```
## Related Skills

- $graph-plan — `agf skill show graph-plan`
- $graph-validate — `agf skill show graph-validate`
- $graph-bugs — `agf skill show graph-bugs`

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
