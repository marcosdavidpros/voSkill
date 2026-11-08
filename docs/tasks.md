# voSkill - Catalogo Detalhado de Tasks do MVP

**Status:** snapshot do grafo em 2026-11-08
**Fonte de verdade:** nodes, ACs, tags e edges em `workflow-graph/graph.db`. Este documento e uma visao humana; atualizar junto com o grafo.
**Escopo:** 22 tasks atomicas dos Epics 1-4. Epic 5 e pos-MVP e permanece bloqueado.

## Premissas de planejamento

- Meio periodo: 20 horas por semana, uma pessoa usando IA no VS Code.
- Sprints de duas semanas; capacidade planejada de ate 30 horas focadas por sprint, reservando o restante para revisao, integracao e imprevistos.
- Tamanhos XP: 20 tasks XS e 2 tasks S. `estimateMinutes` nao esta preenchido; os tamanhos nao equivalem a estimativas cronometradas.
- Todos os nodes de task estao em `backlog`. Os nodes de teste abaixo sao planos e nao foram executados.
- `agf start --scope sprint-1|sprint-2|sprint-3` filtra pelas tags de sprint. O CLI nao tem campo nativo de sprint; os milestones e tags agrupam o trabalho para humanos.

## Sprint 1 - Fundamentos de dados, demandas e cenarios

**Milestone:** `node_a79720461014`
**Dependencia:** inicio do MVP
**Test plans associados:** `node_eb3020370037`, `node_909a5757f67b`, `node_3170fce96b88`, `node_8ce29bd5fa7d`, `node_d239c22106eb` (todos backlog, nao executados).

### Task 1.1.1 - Persistir competencia e rejeitar dados invalidos

- **ID:** `node_b4cb6d7510ae`; **parent:** Task 1.1 (`node_7b64c2f3a241`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** registrar skills manuais com nivel, evidencia, data e autoria; validar entradas atomicamente.
- **AC 1:** Given person P-001 and authorized user U-001, When U-001 saves skill Kubernetes at level 4 with evidence Migração do cluster and review date 2026-11-08, Then reading P-001 returns the exact values, originType=MANUAL, and actorId=U-001.
- **AC 2:** Given a new competency and configured level scale 1..5, When an authorized user submits level 6 or omits required evidence, Then validation identifies the invalid field and no competency record is created.

### Task 1.1.2 - Registrar correcao, historico e autorizacao

- **ID:** `node_b67f892062cb`; **parent:** Task 1.1 (`node_7b64c2f3a241`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** permitir correcao auditavel pela pessoa ou por usuario autorizado e negar alteracoes sem permissao.
- **AC 1:** Given P-001 has current skill level 4, When P-001 or authorized user U-001 corrects it to level 3, Then the current read returns level 3 and the history retains the previous level 4, actorId, and revision timestamp.
- **AC 2:** Given a competency for P-001 and user U-999 without permission, When U-999 submits a correction, Then the system rejects the request with HTTP 403, the current level remains unchanged, and no correction event is added.

### Task 1.2.1 - Extrair sugestoes estruturadas com evidencia

- **ID:** `node_1c5fc434a7cb`; **parent:** Task 1.2 (`node_a9e912b6e9ed`); **prioridade:** Should; **tamanho:** XS.
- **Objetivo:** gerar sugestoes `pending_review` sem alterar o perfil confirmado.
- **AC 1:** Given the source contains Migração do cluster Kubernetes and a test extractor returns skill Kubernetes, level 4, confidence 0.92, and the exact evidence span, When authorized user U-001 requests extraction, Then one suggestion is stored with those exact fields and status pending_review while the confirmed profile is unchanged.
- **AC 2:** Given an empty source or an extractor provider failure, When an authorized user requests extraction, Then the response error.code is EMPTY_SOURCE or PROVIDER_UNAVAILABLE respectively and no suggestion or confirmed competency is stored.

### Task 1.2.2 - Revisar, editar ou rejeitar sugestoes

- **ID:** `node_3dc7d580325f`; **parent:** Task 1.2 (`node_a9e912b6e9ed`); **prioridade:** Should; **tamanho:** XS.
- **Objetivo:** aplicar decisoes humanas de revisao e registrar autor/data.
- **AC 1:** Given suggestion S-001 is pending_review and U-001 is an authorized reviewer, When U-001 accepts or edits S-001, Then its status becomes accepted or edited and the reviewed values enter the confirmed profile with reviewerId U-001 and a revision timestamp.
- **AC 2:** Given suggestion S-001 is pending_review, When authorized reviewer U-001 rejects S-001, Then its status becomes rejected and the confirmed profile remains unchanged.
- **AC 3:** Given suggestion S-001 is pending_review and U-999 has no review permission, When U-999 attempts to accept, edit, or reject it, Then the response is HTTP 403, S-001 remains pending_review, and the confirmed profile remains unchanged.

### Task 1.3.1 - Retornar inferencia rastreavel ou ausencia de evidencia

- **ID:** `node_4f60f9ebc517`; **parent:** Task 1.3 (`node_b0c6a335ef72`); **prioridade:** Should; **tamanho:** XS.
- **Objetivo:** inferir somente a partir de skills-fonte confirmadas e relacoes configuradas, sem alterar o perfil.
- **AC 1:** Given P-001 has confirmed skill Kubernetes and an active relation Kubernetes to OpenShift with confidence 0.65, When an authorized user queries OpenShift fit, Then the response status is inferred, includes relationId and confidence 0.65, and the confirmed profile has no OpenShift skill.
- **AC 2:** Given a missing relation to OpenShift or a missing confirmed source skill for P-001, When an authorized user queries OpenShift fit, Then the response contains no inferred level and reason insufficient_evidence.

### Task 1.3.2 - Validar relacoes entre competencias

- **ID:** `node_b007d1d3ad26`; **parent:** Task 1.3 (`node_b0c6a335ef72`); **prioridade:** Should; **tamanho:** XS.
- **Objetivo:** rejeitar relacoes com skills inexistentes ou confianca fora de 0..1.
- **AC 1:** Given a proposed relation references skill id SKILL-404 that does not exist, When an authorized user saves the relation, Then response error.code is UNKNOWN_SKILL and no relation is stored.
- **AC 2:** Given a proposed relation has confidence 1.2, When an authorized user saves the relation, Then response error.code is INVALID_CONFIDENCE and no relation is stored.

### Task 2.1.1 - Cadastrar demanda por skill e periodo

- **ID:** `node_b14125391b56`; **parent:** Task 2.1 (`node_64c25c38ef0c`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** cadastrar demanda de projeto por skill, nivel, periodo, carga e unidade.
- **AC 1:** Given project P-001 with monthly horizon 2026-01 through 2026-06, skill scale 1..5, and load unit hours, When authorized user U-001 saves Kubernetes level 3 for period 2026-01 with load 40 hours, Then reading the demand returns project P-001, Kubernetes, level 3, 2026-01, load 40, and unit hours and remains editable.
- **AC 2:** Given valid demand rows for 2026-01 and 2026-02, When the user reads P-001's demand schedule, Then both rows are returned with original periods, loads, and units and remain individually editable.
- **AC 3:** Given project P-001 with a six-month horizon, When the user adds valid monthly demands inside that interval, Then every demand is associated with P-001 and no out-of-horizon demand is eligible for optimization.
- **AC 4:** Given a configured load unit hours, When the user submits a demand with unsupported load unit widgets, Then the system rejects the request with error.code INVALID_LOAD_UNIT and does not create a demand row.

### Task 2.1.2 - Rejeitar demanda invalida ou fora do horizonte

- **ID:** `node_65c66feb7ed5`; **parent:** Task 2.1 (`node_64c25c38ef0c`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** impedir que dados de demanda invalidos entrem no schedule ou otimizador.
- **AC 1:** Given a new demand with invalid level 6, negative load, unknown skill, or period outside the configured horizon, When an authorized user saves it, Then the system rejects the request, fieldErrors identifies each invalid field, and no partial demand is created.
- **AC 2:** Given a saved project schedule, When an invalid demand submission is rejected, Then the schedule and all previously saved demand rows remain unchanged.

### Task 2.2.1 - Criar alternativa sem alterar cenario-base

- **ID:** `node_055bb40ca9b5`; **parent:** Task 2.2 (`node_cf0ff3e67229`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** criar uma alternativa isolada com referencia e deltas, preservando o snapshot-base.
- **AC 1:** Given base scenario B-001 with snapshot S-001, When authorized user U-001 creates alternative A-001 changing demand or availability, Then A-001 references B-001, records actorId and createdAt plus the deltas, and S-001 remains byte-for-byte unchanged.
- **AC 2:** Given base scenario id B-404 does not exist, When a user requests an alternative from B-404, Then the system rejects the request with error.code BASE_SCENARIO_NOT_FOUND and creates no alternative.

### Task 2.2.2 - Comparar cenarios e sinalizar entradas ausentes

- **ID:** `node_42cf7ae9ac9d`; **parent:** Task 2.2 (`node_cf0ff3e67229`); **prioridade:** Must; **tamanho:** XS.
- **Objetivo:** comparar premissas/deltas por periodo e identificar cenarios incompletos.
- **AC 1:** Given valid scenarios S-001 and S-002 with monthly demand rows for 2026-01 and 2026-02, When an authorized user compares them, Then the response identifies both scenarios and returns each period's assumptions and changed values without modifying source data.
- **AC 2:** Given S-002 is missing required availability for 2026-02, When an authorized user requests comparison with S-001, Then S-002 is marked incomplete, the missing field and period are listed, and no numeric metric is fabricated.

## Sprint 2 - Otimizacao multiobjetivo e Pareto

**Milestone:** `node_87c4d084738c`; depende da conclusao do Sprint 1.

### Task 3.1.1 - Gerar alternativas viaveis

- **ID:** `node_6848a2c506e7`; **parent:** Task 3.1 (`node_f634c5738eba`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given snapshot S-001 with two confirmed profiles, a project demand, valid availability, and seed 42, When NSGA-II completes with at least two feasible non-dominated strategies, Then each returned alternative has status feasible, an allocation, development actions, separate objective metrics, and run metadata referencing S-001 and seed 42.
- **AC 2:** Given returned alternatives A-001 and A-002, When dominance is evaluated, Then neither alternative dominates the other across all configured objectives.
- **AC 3:** Given all candidate assignments violate hard constraints, When NSGA-II finishes, Then result status is infeasible, conflicting constraint ids are listed, and the feasible alternatives list is empty.
- **AC 4:** Given candidate A-003 assigns 48 hours when P-001 has only 40 available, When feasibility is evaluated, Then the system rejects A-003 with violation capacity_exceeded and excludes it from feasible alternatives.

### Task 3.1.2 - Reportar inviabilidade sem recomendacao invalida

- **ID:** `node_0bf3ae71684f`; **parent:** Task 3.1 (`node_f634c5738eba`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given capacity constraints make every assignment infeasible, When the optimizer completes, Then result status is infeasible, the conflicting constraint ids are returned, and the feasible alternatives list is empty.
- **AC 2:** Given an optimizer candidate violates capacity, When feasibility is evaluated, Then the candidate is excluded from feasible alternatives and its violation is reported as capacity_exceeded.

### Task 3.2.1 - Exibir metricas por alternativa

- **ID:** `node_de2964c14921`; **parent:** Task 3.2 (`node_25ca5d950040`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given Pareto alternative A-001 has objective values coverage 0.80, development 0.60, load 0.70, and cost 1200, When an authorized user opens comparison, Then those exact values are returned under separate objective fields with their units and A-001 identifier.
- **AC 2:** Given A-001 has higher coverage and higher load than A-002, When both are compared, Then both alternatives remain visible and the coverage/load trade-off is shown without a single aggregate ranking.
- **AC 3:** Given alternative A-002 is missing inputs for cost, When its objective vector is displayed, Then cost is marked unavailable with reason missing_cost_input and no numeric value is shown.

### Task 3.2.2 - Sinalizar metricas indisponiveis e trade-offs

- **ID:** `node_734f56ece3ec`; **parent:** Task 3.2 (`node_25ca5d950040`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given A-002 is missing inputs for cost, When the user compares it, Then cost is returned with status unavailable, reason missing_cost_input, and no numeric value.
- **AC 2:** Given A-001 and A-002 trade coverage against load, When the comparison is displayed, Then the conflict is identified and neither alternative is hidden because of a weighted aggregate score.
- **AC 3:** Given comparison request references unknown alternative A-404, When the user requests the comparison, Then the system rejects the request with error.code UNKNOWN_ALTERNATIVE and returns no comparison result.

### Task 3.3.1 - Aplicar restricoes duras de capacidade

- **ID:** `node_497426ad3ef3`; **parent:** Task 3.3 (`node_6a98eb3c4797`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given P-001 has availability 40 hours for 2026-01 and strategy A-001 assigns 48 hours, When the strategy is validated, Then A-001 has status infeasible, violation capacity_exceeded, and is absent from the feasible alternatives list.
- **AC 2:** Given strategy A-002 violates an interest preference but no hard constraint, When feasibility is evaluated, Then A-002 remains feasible and its preference metric is reported separately from capacity violations.

### Task 3.3.2 - Registrar configuracao e reproducao da execucao

- **ID:** `node_87033922065e`; **parent:** Task 3.3 (`node_6a98eb3c4797`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given input snapshot hash H-001, algorithm version V-001, configuration C-001, seed 42, and the same execution environment, When the optimization is run twice, Then both runs return the same metadata and canonical alternatives hash.
- **AC 2:** Given two run records, When an auditor retrieves them, Then each record returns snapshot hash, algorithm version, configuration, seed, and creation timestamp.
- **AC 3:** Given an invalid negative seed -1, When the user requests an optimization run, Then the system rejects the request with error.code INVALID_SEED and creates no run record.

**Planos de teste do Sprint 2 (backlog, ainda nao executados):** `node_57640ad4f6a9`, `node_092f506dde6c`, `node_1f6488757611`.

## Sprint 3 - Dashboard, explicabilidade e governanca humana

**Milestone:** `node_de161370b5b4`; depende da conclusao do Sprint 2.

### Task 4.1.1 - Distinguir cobertura confirmada e inferida

- **ID:** `node_ee603fa2d76b`; **parent:** Task 4.1 (`node_283eecdf5c9b`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given S-001 contains P-001 with Java confirmed level 4, OpenShift inferred confidence 0.65, and Cloud demand without confirmed coverage, When an authorized manager opens the map, Then Java is labeled confirmed, OpenShift inferred, Cloud uncovered, and only confirmed skills count toward coverage.
- **AC 2:** Given OpenShift inference is pending_review, When the map computes coverage, Then it is excluded from confirmed coverage and displays confidence 0.65 and state pending_review.
- **AC 3:** Given the map request references scenario S-404 that does not exist, When the user attempts to open it, Then the system rejects the request with error.code SCENARIO_NOT_FOUND and does not display stale data as current.

### Task 4.1.2 - Exibir risco por limiar configurado

- **ID:** `node_0c05840e7265`; **parent:** Task 4.1 (`node_283eecdf5c9b`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given Kubernetes has a configured critical-skill threshold of 2 confirmed people and S-001 has one confirmed holder P-001, When an authorized manager opens the risk panel, Then the panel shows count 1, threshold 2, skill Kubernetes, person P-001, and the contributing evidence.
- **AC 2:** Given the configured critical-skill threshold is 0, When the risk threshold is saved, Then the system rejects it with error.code INVALID_RISK_THRESHOLD and preserves the previous threshold.

### Task 4.2.1 - Explicar metricas e evidencias da alternativa

- **ID:** `node_9937842c00ea`; **parent:** Task 4.2 (`node_5d13a4a7cb51`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given A-001 has coverage 0.82, load 0.70, cost 1200, snapshot S-001, and evidence ids E-001/E-002, When an authorized user requests explanation with a deterministic test explainer, Then response references A-001/S-001, returns the exact metric values, and every factual claim references E-001 or E-002.
- **AC 2:** Given OptimizationRun returns the objective vector, When the explainer returns narrative text, Then stored metrics remain unchanged and the response labels the metrics deterministic and the narrative generated.
- **AC 3:** Given the LLM explanation service returns an error, When explanation is requested, Then response.error.code is NARRATIVE_UNAVAILABLE, narrative.status is unavailable, and OptimizationRun metrics remain available and unchanged.

### Task 4.2.2 - Declarar incerteza e bloquear alegacoes sem evidencia

- **ID:** `node_8cdd9d3a3c48`; **parent:** Task 4.2 (`node_5d13a4a7cb51`); **prioridade:** Must; **tamanho:** XS.
- **AC 1:** Given A-001 has no cost input, When its explanation is generated, Then cost.status is unavailable, reason is missing_cost_input, and no numeric cost is presented.
- **AC 2:** Given a test explainer returns a factual claim with no metric or evidence reference, When the response is validated, Then unsupportedClaims is empty, uncertainty is true, and reason is missing_evidence.
- **AC 3:** Given the LLM explanation service fails, When an explanation is requested, Then narrative.status is unavailable with reason narrative_unavailable and the deterministic OptimizationRun metrics remain available.

### Task 4.3.1 - Aplicar autorizacao e auditar acesso a perfis

- **ID:** `node_a3e5475acc86`; **parent:** Task 4.3 (`node_a534ddec5be7`); **prioridade:** Must; **tamanho:** S.
- **AC 1:** Given U-999 has no permission to view P-001, When U-999 requests the profile or its export, Then the response is HTTP 403 and contains no protected P-001 fields.
- **AC 2:** Given an access request is denied, When the audit event is stored, Then it contains actorId U-999, resourceId P-001, outcome denied, and no profile name or skill values.

### Task 4.3.2 - Exigir aprovacao humana antes do uso operacional

- **ID:** `node_65a34626233a`; **parent:** Task 4.3 (`node_a534ddec5be7`); **prioridade:** Must; **tamanho:** S.
- **AC 1:** Given alternative A-001 has been generated, When a manager views it, Then the interface labels it decision support and its operational status remains pending_human_approval.
- **AC 2:** Given no authorized human approval exists for A-001, When an API request attempts to apply an allocation or career decision, Then the system rejects the request with error.code HUMAN_APPROVAL_REQUIRED and leaves allocation and career profile unchanged.

**Planos de teste do Sprint 3 (backlog, ainda nao executados):** `node_5dc210693f29`, `node_cb9cce5be1dd`, `node_16bfadac1485`, `node_56075f21eb9c`, `node_16581f45e4be`.

## Dependencias e limites de plano

- Sprint 2 depende do milestone do Sprint 1; suas tasks tambem dependem do milestone do Sprint 1. Sprint 3 depende do milestone do Sprint 2; suas tasks dependem do milestone do Sprint 2.
- Epic 5 e post-MVP e esta bloqueado pelas dependencias aos Epics 1-4.
- Nenhuma task foi executada; os planos de teste estao em backlog.
- O plano nao assume uso de provider LLM especifico; a extracao deve ser validada com fixture deterministica e provider homologado conforme ADR-0001.
