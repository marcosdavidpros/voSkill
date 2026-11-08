# voSkill - Plano de Entrega do MVP

**Status:** proposta de planejamento; revisar apos o primeiro sprint

**Fonte de estado:** grafo local `workflow-graph/graph.db`; este documento e uma visao legivel para humanos.

## Premissas de capacidade

- Meio periodo: 20 horas por semana para uma pessoa, apoiada por agentes de IA no VS Code.
- Cadencia proposta: sprints de duas semanas, 40 horas nominais cada.
- Capacidade planejada: ate 30 horas de trabalho focado por sprint; o restante fica reservado para revisao humana, integracao, reunioes e imprevistos.
- As 22 tarefas de entrega estao majoritariamente em tamanho XP `XS` (20 tarefas) e `S` (2 tarefas). `estimateMinutes` nao esta preenchido e nao ha historico de throughput; por isso, tres sprints sao uma previsao inicial, nao uma data garantida.
- Recalibrar capacidade e estimativas ao fim do Sprint 1 com dados reais de fluxo. A assistencia de IA entra na expectativa de produtividade, mas nao elimina revisao, testes ou integracao.
- O Epic 5 e pos-MVP e fica fora destes sprints, bloqueado ate os Epics 1-4 terminarem e a baseline do piloto ser aprovada.

## Sprint 1 - Fundamentos de dados, demandas e cenarios

**Milestone:** `node_a79720461014`
**Janela:** semanas 1-2
**Capacidade planejada:** ate 30 horas focadas

| ID | Tarefa | Tamanho |
|---|---|---|
| `node_b4cb6d7510ae` | Task 1.1.1 - Persistir competencia e rejeitar dados invalidos | XS |
| `node_b67f892062cb` | Task 1.1.2 - Registrar correcao, historico e autorizacao | XS |
| `node_1c5fc434a7cb` | Task 1.2.1 - Extrair sugestoes estruturadas com evidencia | XS |
| `node_3dc7d580325f` | Task 1.2.2 - Revisar, editar ou rejeitar sugestoes | XS |
| `node_4f60f9ebc517` | Task 1.3.1 - Retornar inferencia rastreavel ou ausencia de evidencia | XS |
| `node_b007d1d3ad26` | Task 1.3.2 - Validar relacoes entre competencias | XS |
| `node_b14125391b56` | Task 2.1.1 - Cadastrar demanda por skill e periodo | XS |
| `node_65c66feb7ed5` | Task 2.1.2 - Rejeitar demanda invalida ou fora do horizonte | XS |
| `node_055bb40ca9b5` | Task 2.2.1 - Criar alternativa sem alterar cenario-base | XS |
| `node_42cf7ae9ac9d` | Task 2.2.2 - Comparar cenarios e sinalizar entradas ausentes | XS |

**Planos de teste associados, ainda nao executados:** `node_eb3020370037`, `node_909a5757f67b`, `node_3170fce96b88`, `node_8ce29bd5fa7d`, `node_d239c22106eb`.

## Sprint 2 - Otimizacao multiobjetivo e Pareto

**Milestone:** `node_87c4d084738c`
**Janela:** semanas 3-4
**Dependencia:** concluir Sprint 1
**Capacidade planejada:** ate 30 horas focadas

| ID | Tarefa | Tamanho |
|---|---|---|
| `node_6848a2c506e7` | Task 3.1.1 - Gerar alternativas viaveis | XS |
| `node_0bf3ae71684f` | Task 3.1.2 - Reportar inviabilidade sem recomendacao invalida | XS |
| `node_de2964c14921` | Task 3.2.1 - Exibir metricas por alternativa | XS |
| `node_734f56ece3ec` | Task 3.2.2 - Sinalizar metricas indisponiveis e trade-offs | XS |
| `node_497426ad3ef3` | Task 3.3.1 - Aplicar restricoes duras de capacidade | XS |
| `node_87033922065e` | Task 3.3.2 - Registrar configuracao e reproducao da execucao | XS |

**Planos de teste associados, ainda nao executados:** `node_57640ad4f6a9`, `node_092f506dde6c`, `node_1f6488757611`.

## Sprint 3 - Dashboard, explicabilidade e governanca humana

**Milestone:** `node_de161370b5b4`
**Janela:** semanas 5-6
**Dependencia:** concluir Sprint 2
**Capacidade planejada:** ate 30 horas focadas

| ID | Tarefa | Tamanho |
|---|---|---|
| `node_ee603fa2d76b` | Task 4.1.1 - Distinguir cobertura confirmada e inferida | XS |
| `node_0c05840e7265` | Task 4.1.2 - Exibir risco por limiar configurado | XS |
| `node_9937842c00ea` | Task 4.2.1 - Explicar metricas e evidencias da alternativa | XS |
| `node_8cdd9d3a3c48` | Task 4.2.2 - Declarar incerteza e bloquear alegacoes sem evidencia | XS |
| `node_a3e5475acc86` | Task 4.3.1 - Aplicar autorizacao e auditar acesso a perfis | S |
| `node_65a34626233a` | Task 4.3.2 - Exigir aprovacao humana antes do uso operacional | S |

**Planos de teste associados, ainda nao executados:** `node_5dc210693f29`, `node_cb9cce5be1dd`, `node_16bfadac1485`, `node_56075f21eb9c`, `node_16581f45e4be`.

## Regras de execucao

- Puxar uma tarefa de cada vez com `agf start --scope sprint-1`, depois `sprint-2` e `sprint-3`, conforme as dependencias.
- As tags `sprint-1`, `sprint-2` e `sprint-3` e as arestas `related_to` associam tarefas aos milestones sem alterar a hierarquia dos Epics 1-4.
- As milestones dependem em sequencia: Sprint 2 depende do Sprint 1; Sprint 3 depende do Sprint 2.
- Executar TDD e validacao na tarefa real; os nos `browser_test` sao planos, nao evidencias de teste executado.
- Fechar uma milestone somente quando todas as suas tarefas e criterios de aceite tiverem sido verificados.

## Limites do CLI

O `agf` instalado nao possui campo/superficie nativa de sprint nem `gate plan`. As milestones e tags permitem visualizar e filtrar o plano, mas `agf insights` pode continuar mostrando `sprintProgress` vazio. `agf forecast` nao tem historico suficiente; o prazo deve ser recalibrado apos o primeiro sprint.
