---
name: graph-deploy
description: Release, DORA, provider choice and cost proof
triggers:
  - graph-deploy
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: DEPLOY
phase: DEPLOY
tokens: ~821
phases: [HANDOFF, LISTENING]
---

# graph-deploy

Release, DORA, provider choice and cost proof. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- HANDOFF approved
- Strictest release gate: harness ≥ 70
- Preparing a release

## Mandatory Flow

```
agf gate deploy → agf forecast → agf metrics --simulate
```

## Steps

Comandos `agf` desta fase (DEPLOY):

| Comando | O que faz |
|---------|-----------|
| `agf provider use <id>` | Choose the provider (openrouter / copilot / ollama) |
| `agf deliver "<request>" --live` | Autonomous end-to-end delivery |
| `agf forecast` | DORA metrics (deploy freq, lead time, CFR, MTTR) |
| `agf metrics --simulate` | Re-price the real bill under all models (cost proof) |
| `agf gate deploy` | Gate DEPLOY (release_check + harness ≥ 70) |

## Flow

```
agf gate deploy → agf forecast → agf metrics --simulate
```

## Exit

- [ ] Release validated
- [ ] Harness ≥ 70 (B)
- [ ] DORA metrics baseline saved
- [ ] Cost simulation reviewed
## Workflow

Step 1: Validate Gate — agf gate deploy (release_check + harness ≥ 70)

Step 2: DORA Metrics — agf forecast (deployment frequency, lead time, CFR, MTTR)

Step 3: Cost Proof — agf metrics --simulate (re-price the real bill under all models)

Step 4: Provider Choice — agf provider use <id> (if you need to switch for release)

Step 5: Deploy — run the project deploy pipeline

Step 6: Post-Deploy Validation — check health checks, logs, metrics

Step 7: Baseline Save — agf snapshot create (post-deploy state)

Step 8: Transition — agf phase LISTENING
## Anti-Patterns

- DO NOT deploy with harness < 70 — the strictest release gate
- DO NOT ignore cost metrics — use --simulate for proof
- DO NOT deploy without a pre-deploy snapshot — required for rollback
- DO NOT skip post-deploy validation — health checks are mandatory
## Output Format

```
Phase: DEPLOY → LISTENING
Release: validated
Harness: score X (≥70 required)
DORA: deploy freq Y/day, lead time P85 Zh, CFR W%, MTTR Vh
Cost: re-priced under N models
Snapshot: pre-deploy + post-deploy
Status: Deployed, monitoring in LISTENING
```
## Related Skills

- $graph-handoff — `agf skill show graph-handoff`
- $graph-listening — `agf skill show graph-listening`

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
