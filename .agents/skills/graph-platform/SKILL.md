---
name: graph-platform
description: Platform audit — web vitals, a11y and harness
triggers:
  - graph-platform
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: VALIDATE
phase: VALIDATE
tokens: ~813
phases: [VALIDATE, DEPLOY]
---

# graph-platform

Platform audit — web vitals, a11y and harness. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Delivery has a UI/platform surface
- During VALIDATE
- Before deploying with a frontend

## Mandatory Flow

```
agf harness → agf quality → agf insights phases → agf eval --suite platform
```

## Steps

Comandos `agf` desta fase (VALIDATE):

| Comando | O que faz |
|---------|-----------|
| `agf harness` | Agent-readiness (8 dimensions, score A/B/C/D) |
| `agf quality` | Gate 95/95 (tests + logs) |
| `agf insights phases` | Health by lifecycle phase |
| `agf eval --suite platform` | Platform-scenario eval |

## Flow

```
agf harness → agf quality → agf insights phases → agf eval --suite platform
```

## Exit

- [ ] Harness ≥ B
- [ ] No a11y/vitals regression
- [ ] Platform eval pass
## Workflow

Step 1: Harness Scan — agf harness (8 dimensions: type coverage, test coverage, architecture fitness, docs, naming, error handling, context density, provenance)

Step 2: Quality Gate — agf quality (95/95: tests + logs over src/)

Step 3: Phase Health — agf insights phases (health distribution by phase)

Step 4: Web Vitals — measure LCP, FID, CLS (if project has UI)

Step 5: Accessibility — WCAG 2.2 AA, ARIA labels, keyboard navigation

Step 6: Platform Eval — agf eval --suite platform (real platform scenarios)

Step 7: Bundle Analysis — check N+1 queries, bundle size

Step 8: Validate — no a11y/vitals regression, harness ≥ B
## Anti-Patterns

- DO NOT deploy with harness < B — platform requires a quality floor
- DO NOT ignore a11y regressions — accessibility is mandatory
- DO NOT skip web vitals in UI projects — performance is a feature
- DO NOT neglect bundle size — it affects LCP and CLS
## Output Format

```
Phase: PLATFORM (VALIDATE parallel)
Harness: score X (grade Y, ≥B required)
Quality: 95/95 — pass/fail
Web Vitals: LCP Xms, FID Yms, CLS Z
Accessibility: WCAG 2.2 AA — pass/fail
Bundle: size X KB, N+1 queries Y
Platform Eval: N scenarios pass
Status: Platform audit passed
```
## Related Skills

- $graph-validate — `agf skill show graph-validate`
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
