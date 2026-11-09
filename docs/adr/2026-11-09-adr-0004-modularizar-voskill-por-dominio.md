---
number: 4
title: Modularizar voSkill por domínio
date: 2026-11-09
status: Accepted
---

# ADR-0004: Modularizar voSkill por domínio

## Status

Accepted

## Context

main.py e database.py concentram contratos e operações de vários domínios; o MVP precisa crescer sem dispersar dependências ou alterar APIs.

## Decision

Manter um monólito FastAPI modular, separar routers e repositories por domínio e extrair a comparação de cenários para uma função pura; evitar uma camada genérica de services ou abstrações sem necessidade.

## Consequences

Melhora coesão e navegabilidade incrementalmente; preserva contratos públicos, injeção atual e Oracle; exige atualizar imports/testes por etapa, com validação completa a cada task.
