# PRD — voSkill: Planejamento Evolutivo de Competências e Alocação de Equipes

**Fase:** PRD (ANALYZE)  
**Versão:** 0.1  
**Status:** Rascunho para validação  
**Metodologias:** 5W2H, JTBD, Pareto, MoSCoW, INVEST, Given/When/Then e matriz de riscos

**Visão e problema**

Equipes de desenvolvimento precisam atender demandas de projetos que mudam ao longo do tempo, desenvolver competências e reduzir dependências em especialistas. Hoje, informações sobre skills, interesses, experiência e demandas podem estar dispersas e não são suficientes, por si só, para comparar planos de alocação e capacitação com seus trade-offs.

O voSkill deve apoiar coordenadores na avaliação de estratégias para os próximos 6 a 12 meses. Em vez de escolher automaticamente uma pessoa para um projeto, o sistema apresenta alternativas de alocação, treinamento, mentoria e rotação, comparadas por objetivos conflitantes e acompanhadas de evidências e explicações. As decisões permanecem sob responsabilidade humana.

**Proposta de valor:** tornar explícitos os efeitos de diferentes planos sobre cobertura de competências, desenvolvimento das pessoas, capacidade futura, carga, risco de conhecimento e custo.

**5W2H:** O sistema organiza dados de competências e demandas e simula alternativas para coordenadores de equipes de software. Será usado no planejamento de capacidade e desenvolvimento, em horizontes configuráveis (inicialmente 6 a 12 meses), com dados fornecidos ou revisados pela organização. O MVP deve permitir uma avaliação demonstrável sem depender de integrações corporativas. O custo operacional e os custos de treinamento devem ser mensuráveis quando os dados correspondentes estiverem disponíveis; não se presume uma meta financeira antes de estabelecer uma linha de base.

**Usuários e JTBD**

**Persona primária:** coordenador ou gestor de equipes de desenvolvimento, responsável por planejar capacidade, reduzir riscos de dependência e apoiar o crescimento das pessoas.

**Persona participante:** pessoa da equipe que revisa suas competências, evidências e interesses e pode contestar ou corrigir informações atribuídas a ela.

**JTBD 1:** Quando planejo projetos futuros, quero comparar estratégias de composição e capacitação, para identificar cobertura e lacunas antes de comprometer a equipe.

**JTBD 2:** Quando uma competência crítica depende de poucas pessoas, quero avaliar alternativas de mentoria, rotação e treinamento, para reduzir o risco sem sobrecarregar a equipe.

**JTBD 3:** Quando discuto o desenvolvimento de uma pessoa, quero considerar seus interesses e mostrar as evidências e limitações dos dados, para apoiar uma conversa transparente sem automatizar decisões de carreira.

**Pareto e priorização MoSCoW**

O maior valor inicial está em combinar inventário revisável de competências, demandas de projeto, simulação e comparação explicável de alternativas. Integrações automáticas e autoajuste dos pesos ficam depois de validar a utilidade do fluxo central.

- **RF-01 (Must):** Quando o coordenador preparar um cenário de planejamento, o sistema deve permitir cadastrar e revisar pessoas, competências, evidências, interesses e demandas, e comparar alternativas sob revisão humana e controles de acesso.
- **RF-02 (Should):** Quando o usuário solicitar extração ou inferência de competências, o sistema deve apresentar sugestões com evidência e confiança para revisão humana; ao comparar cenários, deve exibir alternativas da fronteira de Pareto, seus trade-offs e permitir exportá-las.
- **Could:** integrações com ferramentas de gestão de projetos; dados longitudinais de resultados; calibração experimental de pesos baseada em resultados observados.
- **Won't no MVP:** alocação ou decisão de carreira automática; ingestão invisível de dados de RH ou comunicações; previsões individuais de desligamento; autoaprendizado de pesos sem governança e evidência; prescrição de contratação ou desligamento.

**Premissas, limites e medidas**

- O coordenador e as pessoas autorizadas fornecem ou revisam os dados; a existência de uma evidência não garante que ela continue atual.
- Uma inferência do grafo é uma hipótese de aderência, não uma certificação nem uma skill comprovada.
- A qualidade das alternativas depende da qualidade, atualidade e cobertura dos dados de pessoas e projetos.
- O sistema não deve inferir atributos pessoais sensíveis nem usar as saídas como decisão automatizada de contratação, promoção, remuneração ou desligamento.
- As tecnologias citadas na ideia (pymoo, Neo4j, FastAPI, PostgreSQL, Azure OpenAI, Semantic Kernel e React/Plotly ou Power BI) são candidatas e não decisões de arquitetura deste PRD.

**Métricas de sucesso a instrumentar:** proporção de registros de competências com origem/evidência e revisão identificáveis; cobertura das demandas por cenário; número de alternativas viáveis apresentadas; tempo para preparar e comparar cenários; frequência de revisão/correção dos dados; uso das alternativas em discussões de planejamento; e divergência entre capacidade prevista e observada. Os valores-alvo devem ser definidos após linha de base e validação com usuários. Não se deve otimizar uma métrica isolada à custa de equidade, privacidade ou segurança psicológica.

## Epic 1 — Inventário revisável de competências e governança de dados

Objetivo: permitir que o gestor mantenha um inventário rastreável, corrigível e apropriado ao planejamento, sem tratar inferências como fatos.

### IMPLEMENT: Task 1.1 — Registrar pessoas, competências, níveis e evidências

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** a pessoa P-001, a escala configurada de 1 a 5 e o usuário autorizado U-001, **When** U-001 salvar a skill Kubernetes no nível 4, com evidência “Migração do cluster” e data de revisão 2026-11-08, **Then** a consulta de P-001 retorna exatamente esses valores, `originType=MANUAL` e `actorId=U-001`. [oráculo: valor]
- **Given** uma competência nova e a escala configurada de 1 a 5, **When** um usuário autorizado enviar nível inválido 6 ou omitir a evidência obrigatória, **Then** o sistema rejeita o cadastro com erro de validação, identifica o campo inválido e não cria nenhum registro. [oráculo: valor]
- **Given** que P-001 tem nível vigente 4 para uma skill, **When** P-001 ou U-001 autorizado corrigir o nível para 3, **Then** a leitura atual retorna nível 3 e o histórico preserva nível 4, ator e data da revisão. [oráculo: valor]

### IMPLEMENT: Task 1.2 — Extrair competências de texto com revisão humana

**Prioridade:** Should  
**Tamanho:** M

**Acceptance criteria:**
- **Given** que o texto-fonte contém “Migração do cluster Kubernetes” e o extrator de teste retorna Kubernetes, nível 4, confiança 0.92 e esse trecho exato, **When** um usuário autorizado solicitar a extração, **Then** a sugestão é salva como `pending_review` com esses valores e o perfil confirmado permanece inalterado. [oráculo: valor]
- **Given** uma sugestão `pending_review`, **When** um revisor autorizado aceitar ou editar a sugestão, **Then** o estado passa respectivamente a `accepted` ou `edited` e somente os valores revisados entram no perfil confirmado. [oráculo: humano]
- **Given** uma sugestão `pending_review`, **When** um revisor autorizado rejeitar a sugestão, **Then** o estado passa a `rejected` e o perfil confirmado permanece inalterado. [oráculo: valor]
- **Given** texto vazio, falha do extrator ou revisor sem permissão, **When** o usuário solicitar extração ou revisão, **Then** o sistema retorna `EMPTY_SOURCE`, `PROVIDER_UNAVAILABLE` ou HTTP 403 conforme o caso, sem criar competência confirmada nem evento de revisão não autorizado. [oráculo: propriedade]

### IMPLEMENT: Task 1.3 — Representar relações e inferências entre competências

**Prioridade:** Should  
**Tamanho:** M

**Acceptance criteria:**
- **Given** uma pessoa com uma competência confirmada e uma relação configurada para outra skill, **When** o usuário consultar a aderência relacionada, **Then** o resultado informa estado `inferred`, relação de origem e confiança entre 0 e 1, sem alterar o perfil confirmado. [oráculo: referencia]
- **Given** uma relação ausente ou uma competência-fonte não confirmada para a pessoa, **When** o usuário consultar a aderência à skill-alvo, **Then** o sistema não retorna nível inferido e informa `insufficient_evidence`. [oráculo: propriedade]
- **Given** uma relação que referencia uma skill inexistente, **When** o usuário tentar cadastrá-la, **Then** o sistema retorna `UNKNOWN_SKILL` e não grava a relação. [oráculo: valor]

## Epic 2 — Demandas e simulação de cenários futuros

Objetivo: permitir que o coordenador modele a demanda por projeto e compare situações futuras sem alterar os dados confirmados do cenário-base.

### IMPLEMENT: Task 2.1 — Modelar demandas e horizonte de planejamento

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** o projeto P-001, horizonte mensal 2026-01 a 2026-06, escala de skill de 1 a 5 e unidade de carga `hours`, **When** um usuário autorizado salvar Kubernetes nível 3, período 2026-01 e carga 40, **Then** a leitura retorna projeto, skill, nível, período, carga 40 e unidade `hours`, e a demanda permanece editável. [oráculo: valor]
- **Given** uma demanda com nível 6, carga negativa, skill inexistente ou período fora do horizonte, **When** o usuário tentar salvá-la, **Then** o sistema rejeita o registro, lista o campo inválido e não cria uma demanda parcial. [oráculo: valor]
- **Given** que a unidade de carga configurada é `hours`, **When** o usuário enviar a unidade não suportada `widgets`, **Then** o sistema rejeita a solicitação com `INVALID_LOAD_UNIT` e não cria uma linha de demanda. [oráculo: valor]
- **Given** um projeto com horizonte de seis meses, **When** o usuário adicionar demandas mensais válidas dentro desse intervalo, **Then** cada período é associado ao projeto e nenhuma demanda fora do horizonte aparece como elegível para otimização. [oráculo: propriedade]

### IMPLEMENT: Task 2.2 — Criar e comparar cenários

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** o cenário-base B-001 com snapshot S-001, **When** um usuário autorizado criar um cenário alternativo alterando demanda ou disponibilidade, **Then** o novo cenário referencia B-001, registra autor/data e os deltas, e o snapshot S-001 permanece inalterado. [oráculo: valor]
- **Given** os cenários válidos S-001 e S-002, **When** o usuário compará-los, **Then** a resposta identifica cada cenário e apresenta as premissas e os valores diferentes para cada período sem sobrescrever dados de origem. [oráculo: valor]
- **Given** um cenário sem demanda ou disponibilidade obrigatória, **When** o usuário solicitar comparação, **Then** esse cenário é marcado `incomplete` com a lista dos campos ausentes e nenhuma métrica numérica é inventada para ele. [oráculo: propriedade]

## Epic 3 — Alternativas multiobjetivo para desenvolvimento e alocação

Objetivo: gerar alternativas viáveis e comparáveis que explicitem conflitos entre objetivos, sem declarar uma alternativa universalmente ótima.

### IMPLEMENT: Task 3.1 — Gerar alternativas de alocação, capacitação e mentoria

**Prioridade:** Must  
**Tamanho:** L

**Acceptance criteria:**
- **Given** o snapshot S-001 com dois perfis confirmados, demanda de projeto, disponibilidade válida e seed 42, **When** o NSGA-II concluir com pelo menos duas estratégias viáveis não dominadas, **Then** cada alternativa tem status `feasible`, alocação, ações de desenvolvimento, métricas separadas por objetivo e metadados de execução referenciando S-001 e seed 42. [oráculo: valor]
- **Given** as alternativas retornadas A-001 e A-002, **When** a dominância for calculada, **Then** nenhuma domina a outra considerando todos os objetivos configurados. [oráculo: propriedade]
- **Given** todas as atribuições candidatas violam restrições duras, **When** NSGA-II terminar, **Then** o resultado tem status `infeasible`, lista os IDs das restrições conflitantes e a lista de alternativas viáveis fica vazia. [oráculo: valor]
- **Given** A-003 atribui 48 horas a P-001 quando há somente 40 disponíveis, **When** a viabilidade for avaliada, **Then** o sistema rejeita A-003 com violação `capacity_exceeded` e a exclui das alternativas viáveis. [oráculo: valor]

### IMPLEMENT: Task 3.2 — Comparar objetivos e trade-offs da fronteira de Pareto

**Prioridade:** Must  
**Tamanho:** L

**Acceptance criteria:**
- **Given** A-001 e A-002 têm vetores de objetivos conhecidos, **When** um usuário autorizado abrir a comparação, **Then** cobertura, desenvolvimento, aderência a interesses, carga, bus factor, custo e estabilidade são exibidos separadamente com seus valores de origem. [oráculo: valor]
- **Given** A-001 melhora cobertura mas piora carga em relação a A-002, **When** as alternativas forem comparadas, **Then** ambas permanecem visíveis, o trade-off é identificado e nenhum score agregado não solicitado as ordena. [oráculo: propriedade]
- **Given** A-002 está sem entradas de custo, **When** o usuário compará-la, **Then** custo é retornado como `unavailable`, motivo `missing_cost_input`, sem valor numérico. [oráculo: propriedade]
- **Given** a comparação referencia a alternativa inexistente A-404, **When** o usuário solicitar a comparação, **Then** o sistema rejeita a solicitação com `UNKNOWN_ALTERNATIVE` e não retorna resultado de comparação. [oráculo: valor]

### IMPLEMENT: Task 3.3 — Respeitar carga e restrições declaradas

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** P-001 tem disponibilidade de 40 horas no período 2026-01 e A-001 aloca 48 horas, **When** a estratégia for validada, **Then** A-001 é inviável com violação `capacity_exceeded` e não aparece entre as alternativas viáveis. [oráculo: valor]
- **Given** A-002 viola uma preferência de interesse mas nenhuma restrição dura, **When** a estratégia for avaliada, **Then** A-002 permanece viável e a preferência é reportada como métrica separada, não como erro de capacidade. [oráculo: propriedade]
- **Given** snapshot, versão do algoritmo, configuração, seed 42 e ambiente idênticos, **When** a otimização for executada duas vezes, **Then** os metadados coincidem e o hash canônico das alternativas é igual. [oráculo: metamorfica]
- **Given** seed negativa -1, **When** o usuário solicitar uma execução, **Then** o sistema rejeita a solicitação com `INVALID_SEED` e não cria registro de execução. [oráculo: valor]

## Epic 4 — Dashboard explicável e apoio à decisão humana

Objetivo: tornar alternativas, dados de origem, incertezas e limitações compreensíveis para uma discussão de planejamento.

### IMPLEMENT: Task 4.1 — Visualizar competências, lacunas e riscos

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** o cenário S-001 contém P-001 com Java confirmado nível 4, OpenShift inferido confiança 0.65 e demanda Cloud sem cobertura confirmada, **When** um gestor autorizado abrir o mapa, **Then** os três estados são visualmente distintos e a cobertura conta apenas competências confirmadas. [oráculo: valor]
- **Given** o limiar configurado para risco de dependência da skill Kubernetes é 2 pessoas confirmadas e o cenário tem 1 pessoa confirmada, **When** o painel de risco for exibido, **Then** mostra a contagem 1, o limiar 2, a skill, a pessoa e as evidências consideradas, sem depender de um limiar universal fixo. [oráculo: valor]
- **Given** a inferência OpenShift está pendente de revisão, **When** o mapa calcular a cobertura, **Then** ela não é contabilizada como competência confirmada e aparece com confiança 0.65 e estado de revisão. [oráculo: propriedade]
- **Given** o mapa solicitado referencia o cenário inexistente S-404, **When** o usuário tentar abri-lo, **Then** o sistema rejeita a solicitação com `SCENARIO_NOT_FOUND` e não exibe dados de um cenário anterior como se fossem atuais. [oráculo: valor]

### IMPLEMENT: Task 4.2 — Explicar e comparar alternativas

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** a alternativa A-001 contém métricas coverage 0.82, load 0.70 e cost 1200, snapshot S-001 e evidências E-001/E-002, **When** um usuário autorizado solicitar explicação, **Then** a resposta identifica A-001/S-001, reporta esses valores sem alterá-los e associa cada afirmação factual à métrica/evidência correspondente. [oráculo: referencia]
- **Given** a explicação contém texto narrativo gerado por LLM e métricas calculadas deterministicamente, **When** o resultado for apresentado, **Then** as duas origens são rotuladas separadamente e o LLM não pode modificar os valores do vetor de objetivos. [oráculo: propriedade]
- **Given** uma métrica de A-001 não tem dados de entrada, **When** a explicação for gerada, **Then** a métrica aparece `unavailable` com o motivo e não recebe valor numérico. [oráculo: propriedade]
- **Given** uma afirmação narrativa não possui evidência vinculada ou o serviço LLM retorna erro, **When** a explicação for gerada, **Then** `unsupportedClaims` fica vazio, a resposta declara `missing_evidence` ou `error.code=NARRATIVE_UNAVAILABLE` e as métricas determinísticas permanecem disponíveis. [oráculo: propriedade]

### IMPLEMENT: Task 4.3 — Proteger dados e manter supervisão humana

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** U-999 não tem permissão para visualizar o perfil de P-001, **When** U-999 solicitar o perfil ou sua exportação, **Then** a resposta é HTTP 403, não contém campos pessoais de P-001 e registra a tentativa sem copiar o conteúdo protegido para o log. [oráculo: propriedade]
- **Given** A-001 foi gerada pelo otimizador, **When** um gestor a consultar, **Then** é identificada como apoio à decisão e exige aprovação humana antes do uso operacional. [oráculo: humano]
- **Given** qualquer usuário solicitar uma alocação final ou decisão de carreira automática, **When** a solicitação for processada, **Then** o sistema rejeita a execução e não altera as alocações nem o perfil de carreira da pessoa. [oráculo: propriedade]

**Decomposição da tarefa:**

- Task 4.3.1 — Aplicar autorização e auditar acesso a perfis.
- Task 4.3.2 — Exigir aprovação humana antes do uso operacional.

**Requisitos não funcionais**

- **Privacidade e segurança:** minimizar dados pessoais; restringir acesso por função; registrar acessos e alterações relevantes; proteger dados em trânsito e em repouso conforme a política do ambiente; permitir correção e remoção conforme governança definida antes do uso real.
- **Transparência:** mostrar origem, data, confiança e estado de revisão de dados; diferenciar observação, inferência e recomendação; disponibilizar premissas, objetivos e restrições considerados.
- **Confiabilidade:** validar entradas e restrições; indicar falhas ou ausência de solução sem fabricar resultados; registrar configuração e versão dos dados usadas em cada execução.
- **Usabilidade e acessibilidade:** permitir comparar cenários e alternativas sem depender exclusivamente de cor; apresentar definições das métricas e linguagem adequada a gestores e participantes.
- **NFR-PERF-01 — Performance efficiency:** Após medir o workload do piloto, configurar metas de response time; registrar p95, throughput, memória, falhas, versão e configuração. Exibir progresso e permitir cancelar uma execução sem persistir resultado parcial como concluído. Não fixar limites numéricos antes da baseline.

**Mapa de aplicabilidade NFR — ISO/IEC 25010**

| Dimensão | Mapeamento | Escopo |
|---|---|---|
| Functional suitability | Epics 1–4: inventário, cenários, otimização e dashboard | MVP |
| Performance efficiency | NFR-PERF-01; Epic 3 mede resposta/recursos após baseline do piloto | MVP, metas após baseline |
| Compatibility | NFR-COMP-01; Epic 5, conectores com fontes aprovadas e mapeamentos versionados | Pós-MVP |
| Interaction capability | NFR-ACC-01; Task 4.1.1, navegação por teclado, estados textuais e nomes acessíveis | MVP |
| Reliability | NFR-REL-01; Task 3.1.2, falha não persiste resultado parcial como concluído | MVP |
| Security | NFR-SEC-01; Task 4.3.1, autorização, exportação e auditoria sem PII em logs | MVP |
| Maintainability | ADR-0001, arquitetura modular; contratos SkillSuggestion e OptimizationRun | MVP |
| Flexibility | ADR-0001, adapters de LLM; Epics 2–3, cenários e parâmetros de objetivo configuráveis | MVP |
| Safety | ADR-0002 e Task 4.3.2, revisão/aprovação humana e sem decisão automática sobre pessoas | MVP |

**NFRs genéricos adicionais**

- **Security:** NFR-SEC-01.
- **Reliability:** NFR-REL-01.
- **Performance:** NFR-PERF-01; os limites serão definidos após a baseline, não presumidos.
- **Accessibility:** NFR-ACC-01.
- **Scalability:** NFR-SCL-01, Epic 5; adiado até haver workload representativo e metas acordadas após o piloto.

**Epic 5 pós-MVP — Integrações e escalabilidade além do piloto**

Epic 5 depende da conclusão dos Epics 1–4 e da aprovação da baseline de workload do piloto. Task 5.1 implementará conectores aprovados com contratos/mapeamentos versionados e consentimento; Task 5.2 medirá escalabilidade além do piloto a partir da baseline. Não iniciar integrações sem autorização e contratos de dados aprovados; não declarar conformidade de escala antes da medição.

**Fora de escopo do MVP**

- Conectores automáticos para Jira, Azure DevOps, RH, transcrições, e-mail ou repositórios.
- Escalabilidade para volumes acima do workload acordado para o piloto; será medida e planejada no Epic 5 a partir de uma baseline real.
- Decisões automáticas de contratação, promoção, remuneração, desligamento ou alocação final.
- Predição de desempenho, propensão a desligamento ou avaliação individual baseada em dados não revisados.
- Evolução automática dos pesos do fitness. Esta hipótese exige dados de resultados, governança, avaliação de vieses e validação antes de entrar em escopo.
- Definição de um provedor LLM, banco de grafos, biblioteca de otimização, backend ou framework de dashboard; essas decisões pertencem à fase de DESIGN.

**Matriz de riscos**

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Dados desatualizados ou incompletos produzem alternativas enganosas | Alta | Alto | Mostrar origem e data; permitir revisão; sinalizar lacunas e impedir uso silencioso de dados inválidos. |
| Extração de LLM ou inferências reproduzem vieses ou alucinam competências | Média | Alto | Revisão humana obrigatória; evidência citada; confiança explícita; separar sugestão de dado confirmado; monitorar correções e rejeições. |
| Gestores interpretam score como decisão objetiva sobre pessoas | Média | Alto | Exibir trade-offs, limitações e caráter consultivo; proibir decisão automatizada; validar linguagem e fluxo com usuários. |
| Exposição indevida de dados de pessoas | Média | Alto | Minimização, controle de acesso, auditoria, retenção definida e testes de autorização antes de piloto com dados reais. |
| Pesos ou métricas favorecem uma dimensão e prejudicam outras | Média | Alto | Expor métricas separadas e fronteira de Pareto; não esconder pesos; adiar autoajuste até validação e governança. |
| Otimizador retorna estratégia inviável ou difícil de reproduzir | Média | Médio | Validar restrições; registrar entradas e configuração; identificar inviabilidade e permitir repetição auditável. |

**Dependências e questões em aberto**

- Definir participantes do piloto, responsáveis pelos dados e processo de consentimento/revisão antes de usar informações reais.
- Definir escala de níveis de competência, unidade de carga, disponibilidade, horizonte e regra de atualização dos dados.
- Definir como serão estimados custo, desenvolvimento, estabilidade e bus factor, incluindo tratamento de dados ausentes.
- Confirmar quais restrições de alocação são obrigatórias e quais são preferências negociáveis.
- Selecionar tecnologias e estratégia de implantação na fase de DESIGN, considerando requisitos de privacidade, segurança, custo e operação.
- Definir linha de base e metas de sucesso após entrevistas com usuários e observação do processo atual.

**Próxima fase**

Validar este PRD com coordenadores e participantes de equipe; então executar `agf import-prd docs/_internal/prd/voskill.md --dry-run`, revisar os nós extraídos e só depois importar ao grafo. Próxima skill: `graph-analyze`.