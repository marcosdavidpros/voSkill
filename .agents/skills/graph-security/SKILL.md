---
name: graph-security
description: Security audit (OWASP / STRIDE / secrets)
triggers:
  - graph-security
version: 2.0.0
author: auto-generated
date: 2026-11-06
category: REVIEW
phase: REVIEW
tokens: ~773
phases: [REVIEW, DEPLOY]
---

# graph-security

Security audit (OWASP / STRIDE / secrets). Dirija tudo pelo CLI `agf` — **zero MCP**. Carregue contexto com
`agf context <id>` antes de mudar qualquer coisa.

## When to Use

- Change touches authn/authz, external I/O or secrets
- Gate parallel to harness
- Before deploying sensitive features

## Mandatory Flow

```
agf check <id> → agf scan-repos → agf node add --type risk
```

## Steps

Comandos `agf` desta fase (REVIEW):

| Comando | O que faz |
|---------|-----------|
| `agf check <id>` | Includes the per-task security gate |
| `agf harness` | Agent-readiness (parallel to security) |
| `agf node add --type risk` | Record security findings as traceable risk |
| `agf scan-repos` | Scan neighbor repos for known vulnerabilities |

## Flow

```
agf check <id> → agf scan-repos → agf node add --type risk
```

## Exit

- [ ] No critical secret/vuln
- [ ] Findings tracked in graph as risk nodes
- [ ] Security gate pass
## Workflow

Step 1: Per-Task Check — agf check <id> (per-task security gate)

Step 2: Repo Scan — agf scan-repos (npm audit, secrets grep, Zod boundaries)

Step 3: STRIDE Analysis — identify threats by category (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation)

Step 4: Register Findings — agf node add --type risk (traceable findings in the graph)

Step 5: Mitigate — create tasks to fix critical/high findings

Step 6: Validate — confirm no critical secret/vuln remains
## Anti-Patterns

- DO NOT ignore security findings — always track as risk nodes
- DO NOT assume harness covers security — they are parallel gates
- DO NOT deploy with critical vulns — fix before DEPLOY
- DO NOT skip neighbor-repo scan — supply chain matters
## Output Format

```
Phase: SECURITY (REVIEW parallel)
Findings: N risks registered (K critical, M high, J medium)
Secrets: scan result
Vulns: npm audit result
STRIDE: threat categories covered
Gate: security pass/fail
Status: Security gate passed
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
