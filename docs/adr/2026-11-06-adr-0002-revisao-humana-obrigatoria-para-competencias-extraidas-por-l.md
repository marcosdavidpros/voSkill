---
number: 2
title: Revisão humana obrigatória para competências extraídas por LLM
date: 2026-11-06
status: Accepted
---

# ADR-0002: Revisão humana obrigatória para competências extraídas por LLM

## Status

Accepted

## Context

O PRD exige que competências, níveis e evidências extraídos de textos não sejam tratados como fatos sem revisão, e proíbe decisões automatizadas de carreira.

## Decision

Toda extração de competência por LLM é uma sugestão não verificada que inclui skill, nível sugerido, confiança e evidência de origem. Uma pessoa autorizada pode aceitar, editar ou rejeitar; somente sugestões aceitas passam ao inventário confirmado. Nenhuma saída do sistema executa decisão de contratação, promoção, remuneração, desligamento ou alocação final.

## Consequences

O produto precisa registrar estado de revisão e proveniência, distinguir sugestão de competência confirmada e permitir correção. A otimização só pode tratar dados confirmados como evidência e deve sinalizar inferências. O fluxo exige revisão humana antes de qualquer uso operacional.
