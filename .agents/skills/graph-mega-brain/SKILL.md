---
name: graph-mega-brain
description: Drive all 9 phases as a self-improving spiral: pull → brief → build (autonomous or delegated) → submit/done → measure → learn → next. Each turn calibrates the next.
triggers:
  - graph-mega-brain
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: ORCHESTRATION
phase: ORCHESTRATION
tokens: ~1649
phases: [LEAD, IMPLEMENT, VALIDATE]
---

# graph-mega-brain

Drive all 9 phases as a self-improving spiral: pull → brief → build (autonomous or delegated) → submit/done → measure → learn → next. Each turn calibrates the next.. Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Drive a PRD/feature end-to-end through the graph (ANALYZE→…→LISTENING)
- Delegate the build to any driving CLI (no provider needed) or cheap headless executors
- Token cost matters: RAG + tier-router + gates + telemetry instead of generating everything

## Mandatory Flow

```
agf stats → [per phase: agf phase → phase cmds → agf brief → build → agf submit|done → agf check/gate] → agf savings → agf learning/heal → agf next (calibrated)
```

## Steps

Comandos `agf` desta fase (ORCHESTRATION):

| Comando | O que faz |
|---------|-----------|
| `agf stats / agf query` | Pre-flight: reconcile graph (code/graph beat memory) |
| `agf phase` | Detect current phase (SHAPE→BUILD→SHIP) |
| `agf next` | Pull next task (WIP=1) |
| `agf brief <id>` | Delegation spec; --live cmds return mode:delegated when no provider |
| `agf submit <id> --result <json>` | Close delegated build: validate → blast → DoD → done; deviations → findings |
| `agf done <id>` | Close autonomous build: blast + savings + done + suggest next |
| `agf gate <phase>` | Phase readiness gate |
| `agf gaps` | Detect completeness gaps → delegate fix → re-verify |
| `agf savings / agf metrics --economy-report` | Measure the turn (counterfactual, labeled) |
| `agf insights flow` | Flow A/B verdict (flow_on vs flow_off token savings) |
| `agf learning stats / agf heal` | Learn + self-heal → calibrate the next turn |

## Flow

```
agf stats → [per phase: agf phase → phase cmds → agf brief → build → agf submit|done → agf check/gate] → agf savings → agf learning/heal → agf next (calibrated)
```

## Exit

- [ ] All 9 phases driven, gate passed each
- [ ] Build delegated (brief → submit) or autonomous (--live → done); return validated by parse, not re-read
- [ ] Each turn measured + fed back (savings → learning) — a spiral, not a circle
- [ ] Loose ends become finding/risk — never done on a false claim
## Workflow

Step 1: Pre-flight — agf stats / agf query; reconcile (code/graph beat memory)

Step 2: Per phase — agf phase detects; run the phase agf commands and pass the gate (see graph-<phase>)

Step 3: Reuse before generating (anti-meme) — apply the chain in order: rag-in (agf retrieve-command) → rag-out (agf scaffold/agf montar-output) → artifact_reuse (exact-hit) → repo_map (input cut) → flow (agf context dilutes the neighbourhood by Φ; pinned invariants kept — PIN what matters first, flow only drops UNPINNED peripheral nodes; ~77-88% input cut, zero defect increase when pinned) → rag-cache (response_cache, autonomous only). Generate only the genuine delta.

Step 4: Brief — agf brief <id>; fill the <fill:> judgment calls (imitate, read/touch, contract, testWith)

Step 5: Build — FIRST check the mode: `agf status` (data.mode). DELEGATED (you are a modern CLI = the brain): implement the brief yourself, apply the edits, close via `agf submit`. AUTONOMOUS (agf has its own provider): `agf autopilot/run/deliver --live`. If you ARE a modern CLI but status says autonomous, the driver marker mismatched (data.modeReason) — drive delegated anyway (brief→submit) and report the mismatch so the marker gets fixed.

Step 6: Close — delegated: agf submit <id> --result {arquivos,testes,desvios} (validate→blast→DoD→done, deviations→findings). autonomous: agf check <id> → agf done <id>

Step 7: Measure — agf savings / agf metrics --economy-report (counterfactual vs labeled baseline)

Step 8: Learn (close the spiral) — agf savings/insights flow show the economy; agf submit/agf done already record the outcome so Φ(flow) rises → next turn dilutes more; agf learning stats|route + agf heal + agf gaps re-verify → calibrate → agf next; each turn smarter than the last
## Anti-Patterns

- NO one-shot of the whole system — decompose (agf decompose) and delegate per task
- NO generating what you can retrieve — RAG before the LLM is the whole economy
- NO frontier for everything — route by tier; frontier only for reasoning
- NO trusting memory progress counts — reconcile graph + code
- NO skipping the gate to go green — fix the work or record the gap honestly
- NO re-reading the executor diff to validate — use agf submit (parse the structured return)
- NO circle without feedback — measure (savings) + learn (learning/heal) each turn or it never improves
## Output Format

```
Cycle: <feature/PRD> | Phase: <CURRENT> → <NEXT>
Reconcile: <graph delta, if any>
Mode: <autonomous|delegated> (provider <via>, or none)
Build: <N tasks closed via submit/done, validated M/N>
Gate: <agf gate/check> — <pass/fail, score/harness>
Economy: <tokens/$ this turn, saved vs baseline (method)>
Learned: <thresholds/routing adjusted from this turn>
Findings: <loose ends as finding/risk, or "none">
Next: <next action / phase>
```
## Related Skills

- $graph-lead — `agf skill show graph-lead`
- $graph-implement — `agf skill show graph-implement`
- $graph-validate — `agf skill show graph-validate`
## Constraints

- CLI-first: everything via agf — zero MCP. Build is autonomous (provider) or delegated (any driving CLI via brief→submit)
- The conductor does not hand-write production code — it briefs, delegates, verifies
- WIP=1, pull (agf next); honesty: never done on a false claim
- It is a spiral, not a circle: every turn feeds savings→learning back into the next

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
