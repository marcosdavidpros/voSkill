---
number: 5
title: Objetivos do otimizador NSGA-II no MVP
date: 2026-11-09
status: Accepted
---

# ADR-0005: Objetivos do otimizador NSGA-II no MVP

## Status

Accepted

## Context

O PRD requer alternativas não dominadas, métricas separadas e não fabricar valores quando faltam inputs. O schema atual tem proficiência confirmada, demanda por nível/carga e disponibilidade; não há inputs confiáveis de custo, bus factor, estabilidade ou interesses.

## Decision

Usar pymoo/NSGA-II conforme ADR-0001. No MVP, minimizar skill_gap_hours (lacuna entre nível demandado e nível confirmado, ponderada por load_amount) e peak_utilization (maior razão carga/alocação sobre disponibilidade por pessoa/período). Tratar capacidade como hard constraint; gerar development_actions para skill gaps sem alterar o perfil. Não incluir métricas sem inputs.

## Consequences

O vetor permanece explícito e cada métrica é retornada separadamente; cenários com inputs diferentes podem gerar trade-offs. Métricas custo, estabilidade, interesse e bus factor ficam indisponíveis até haver fontes e fórmulas acordadas. O resultado é apoio à decisão e não altera alocação nem perfil.
