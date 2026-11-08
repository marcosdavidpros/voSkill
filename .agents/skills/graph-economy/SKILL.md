---
name: graph-economy
description: Enable/measure the opt-in bio/math token-economy levers (agf economy). Each is grounded in a paper/biology, default OFF (byte-identical), and observable as JSON via --select.
triggers:
  - graph-economy
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: OPTIMIZE
phase: OPTIMIZE
tokens: ~1227
phases: [MEGA-BRAIN, IMPLEMENT, DEPLOY]
---

# graph-economy

Enable/measure the opt-in bio/math token-economy levers (agf economy). Each is grounded in a paper/biology, default OFF (byte-identical), and observable as JSON via --select.. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Token cost matters and you want deterministic, opt-in input cuts beyond the always-on RAG/repo-map
- Before a long autopilot run: turn on the safe levers, then measure savings vs baseline
- You see redundant prior-memory injection, marginal compressions, or premature swarm fan-out

## Mandatory Flow

```
agf economy list → agf economy on <lever> → [run tasks/autopilot] → agf metrics --economy-report → agf savings
```

## Steps

Comandos `agf` desta fase (OPTIMIZE):

| Comando | O que faz |
|---------|-----------|
| `agf economy list` | List all levers with enabled flag + cumulative saved tokens (JSON) |
| `agf economy on <lever>` | Enable one lever (project setting; default all-OFF) |
| `agf economy off <lever>` | Disable one lever |
| `agf metrics --economy-report` | Per-lever savings + tokens/$ this session |
| `agf savings` | Cumulative token economy per task (real ledger) |
| `agf gc --consolidate --dry-run` | Preview sleep-consolidation of near-duplicate memories |
| `agf calibrate` | Calibrate the RAG gate threshold from the lever ledger |

## Flow

```
agf economy list → agf economy on <lever> → [run tasks/autopilot] → agf metrics --economy-report → agf savings
```

## Exit

- [ ] Chosen levers enabled and visible in agf economy list
- [ ] Savings measured (agf metrics --economy-report / agf savings) against a labeled baseline
- [ ] No defect-rate regression — disable any lever that trades correctness for tokens
## Workflow

Step 1: Inspect — agf economy list --select data.levers (see enabled + saved per lever)

Step 2: Pick safe reallocators first — agf economy on budget_kleiber (Kleiber 3/4 budget) · agf economy on heat_kernel (e^{-tL} repo-map ranking). Saved≈0; they reshape, not cut

Step 3: Add input-cutters — ncd_dedup (Kolmogorov/NCD dup memories) · forage_stop (Charnov MVT) · context_diff (predictive-coding + Bloom; skip already-sent tool output) · mdl_select (Rissanen MDL; drop marginal compressions) · info_bottleneck (Tishby IB gate on caveman)

Step 4: Heavier infra — stigmergy (Dorigo ACO pheromone trails across tasks) · consolidation (run agf gc --consolidate; Tononi–Cirelli SHY) · zipf_estimate (calibrated chars/token) · quorum_gate (bacterial quorum sensing on A2A broadcast)

Step 5: Exercise — run agf autopilot / deliver / a few agf start→done cycles so the levers act and record events

Step 6: Measure — agf metrics --economy-report and agf savings; compare saved vs the cost (defect rate). Keep net-positive levers, off the rest
## Anti-Patterns

- DO NOT enable every lever blindly — turn on, measure, keep only net-positive
- DO NOT claim savings a lever did not make — read the ledger (agf economy list / agf metrics), do not estimate
- DO NOT treat reallocators (budget_kleiber, heat_kernel) as token cuts — their saved is ~0 by design
- DO NOT run agf gc --consolidate without --dry-run first — it deletes redundant memory files
## Output Format

```
Levers enabled: <names>
Saved (ledger): <tokens, by lever>
Method: agf metrics --economy-report (counterfactual vs labeled baseline)
Verdict: <net-positive levers kept | levers disabled and why>
```
## Related Skills

- $graph-mega-brain — `agf skill show graph-mega-brain`
- $graph-implement — `agf skill show graph-implement`
- $graph-deploy — `agf skill show graph-deploy`
## Constraints

- Every lever is opt-in and default OFF → byte-identical until enabled
- CLI-first: toggle via agf economy, measure via agf metrics/savings — zero MCP
- Honesty: a lever that raises the defect rate is net-negative even if it saves tokens

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
