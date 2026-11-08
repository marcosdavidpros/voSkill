---
number: 1
title: Stack candidata do MVP voSkill
date: 2026-11-06
status: Accepted
---

# ADR-0001: Stack candidata do MVP voSkill

## Status

Accepted

## Context

O PRD define um MVP com:

- inventário revisável de competências;
- cadastro manual de skills;
- simulação de cenários;
- otimização multiobjetivo;
- dashboard explicável;
- supervisão humana obrigatória.

A proposta inicial considerava PostgreSQL, Neo4j, pymoo e React. Entretanto, já existe disponibilidade de infraestrutura Oracle e o objetivo do MVP é validar a abordagem de competências, cenários e otimização, minimizando a complexidade operacional.

## Decision

O MVP adotará uma arquitetura modular composta por:

### Persistência

- Oracle como repositório principal de dados.
- Todas as entidades do domínio serão armazenadas inicialmente em Oracle.

Exemplos:

- Pessoa
- Skill
- Competência
- Relações entre skills
- Projetos
- Demandas
- Cenários
- Resultados de otimização

### Grafo de Competências

A modelagem de competências será implementada inicialmente através de:

- tabelas relacionais em Oracle;
- grafo em memória utilizando NetworkX.

O uso de Neo4j fica adiado para avaliação futura após validação da necessidade de um banco de grafos dedicado.

### API

- Python
- FastAPI

### Otimização Evolutiva

- pymoo
- NSGA-II

Responsável por gerar cenários de:

- alocação;
- capacitação;
- sucessão;
- desenvolvimento de competências.

### Inteligência Artificial

Será utilizada uma camada de abstração para LLMs.

A implementação inicial dará preferência a soluções já homologadas pela organização, como:

- GitHub Models;
- GitHub Copilot Enterprise (quando disponível via API).

Alternativamente poderão ser utilizados:

- OpenRouter;
- Azure OpenAI;
- OpenAI;
- Anthropic Claude;
- Gemini.

Nenhuma inferência gerada por LLM poderá produzir decisões automáticas sobre pessoas.

Todas as inferências devem ser:

- rastreáveis;
- auditáveis;
- revisáveis por humanos.

### Visualização

- React
- Plotly

### Explicabilidade

Será criado um serviço dedicado de explicação para converter resultados da otimização em linguagem compreensível para gestores.

Exemplos:

- impactos em bus factor;
- cobertura de skills;
- riscos;
- desenvolvimento das pessoas;
- trade-offs entre cenários.

## Architecture Overview

```text
React + Plotly
       │
       ▼
    FastAPI
       │
 ┌─────┼─────────────────┐
 │     │                 │
 ▼     ▼                 ▼

Oracle  LLM Adapter   NetworkX
 │         │              │
 │         ▼              │
 │   GitHub Models        │
 │   OpenRouter           │
 │   Azure OpenAI         │
 │                        │
 └────────┬───────────────┘
          │
          ▼

   Scenario Engine
          │
          ▼

   NSGA-II (pymoo)
          │
          ▼

 Explanation Service
          │
          ▼

 Dashboard