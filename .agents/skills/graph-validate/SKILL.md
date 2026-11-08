---
name: graph-validate
description: E2E, acceptance criteria, product-relevant eval and metrics
triggers:
  - graph-validate
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: VALIDATE
phase: VALIDATE
tokens: ~1002
phases: [IMPLEMENT, REVIEW]
---

# graph-validate

E2E, acceptance criteria, product-relevant eval and metrics. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- ≥50% of tasks done with AC
- Before REVIEW
- Verifying a complete sprint

## Mandatory Flow

```
agf kanban → agf check <id> (task) → agf eval --live → agf quality → agf forecast → agf metrics → agf gate validate → agf phase REVIEW
```

## Steps

Comandos `agf` desta fase (VALIDATE):

| Comando | O que faz |
|---------|-----------|
| `agf kanban` | Show current sprint board |
| `agf check <id>` | DoD + TDD per task |
| `agf eval --live` | Real-scenario suite → scorecard (resolve% × cost) |
| `agf quality` | Gate 95/95 (tests + logs over src/) |
| `agf metrics` | Tokens/$ per task and session (real ledger) |
| `agf forecast` | DORA metrics (change failure rate, lead time, MTTR) |
| `agf gate validate` | Gate VALIDATE → REVIEW |

## Flow

```
agf kanban → agf check <id> (task) → agf eval --live → agf quality → agf forecast → agf metrics → agf gate validate → agf phase REVIEW
```

## Exit

- [ ] All sprint tasks validated
- [ ] AC pass rate meets threshold
- [ ] No critical test failures
- [ ] done_integrity and status_flow pass
- [ ] Harness no regression >10pts
## Workflow

Step 1: Identify Scope — agf kanban, filter done column of current sprint

Step 2: Task Validation — agf check <id> per task (DoD 8 checks)

Step 3: AC Quality — agf check <id> (INVEST scoring, measurability bonus)

Step 4: Run Tests — npx vitest run (unit + integration), npx vitest run tests/integration/ (E2E)

Step 5: Done Integrity — agf check <id> (all done nodes meet DoD)

Step 6: Status Flow — agf check <id> (valid transitions: backlog → in_progress → done)

Step 7: Scenario Coverage — agf insights (user scenarios covered by implemented tasks)

Step 8: DORA Quality — agf forecast (change failure rate <5%, lead time P85 <24h, MTTR <1h)

Step 9: Sprint Metrics — agf metrics (completion rate, AC pass rate, avg time vs estimates)

Step 10: Validate Gate — agf gate validate (all tasks validated, AC pass, no critical failures)

Step 11: Transition — agf phase REVIEW
## Anti-Patterns

- DO NOT skip E2E tests — unit tests alone are insufficient
- DO NOT mark validation passed if tests fail — fix first
- DO NOT ignore flaky tests — investigate and fix root cause
- DO NOT validate tasks still in_progress — complete first
- DO NOT skip agf check for done tasks — catches DoD violations missed during IMPLEMENT
- DO NOT ignore done_integrity — catches DoD violations missed during IMPLEMENT
## Output Format

```
Phase: VALIDATE → REVIEW
Tasks validated: N/M passed
Tests: N passed, M failed
AC pass rate: X%
DORA: change failure rate Y%, lead time P85 Zh
Gate: validate_ready — score N/100, grade X
Status: Ready to proceed to REVIEW phase
```
## Related Skills

- $graph-implement — `agf skill show graph-implement`
- $graph-review — `agf skill show graph-review`

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
