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

- **Must:** cadastro/importação manual de pessoas, competências, evidências e interesses; cadastro de demandas; cenários futuros; geração de alternativas multiobjetivo; comparação de trade-offs; revisão humana; controles básicos de acesso e privacidade.
- **Should:** assistência de LLM para extrair competências de textos fornecidos pelo usuário; inferências entre competências relacionadas com confiança explícita; fronteira de Pareto visualizada; exportação de resultados para discussão.
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

### Task 1.1 — Registrar pessoas, competências, níveis e evidências

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um usuário autorizado e uma pessoa cadastrada, **When** registrar uma competência, **Then** o sistema guarda skill, nível, origem/evidência, data de revisão e autoria, sem exigir que uma inferência seja registrada como fato.
- **Given** uma competência registrada, **When** a pessoa ou um usuário autorizado corrigi-la, **Then** a versão vigente e o histórico de alteração ficam distinguíveis e a correção aparece nas consultas subsequentes.

### Task 1.2 — Extrair competências de texto com revisão humana

**Prioridade:** Should  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um texto fornecido para análise, **When** a extração assistida estiver disponível, **Then** cada sugestão inclui competência, nível sugerido, confiança e trecho de evidência, identificados como sugestões não verificadas.
- **Given** sugestões produzidas, **When** um usuário revisá-las, **Then** somente itens explicitamente aceitos ou editados passam a compor o inventário confirmado; rejeições não alteram o perfil confirmado.

### Task 1.3 — Representar relações e inferências entre competências

**Prioridade:** Should  
**Tamanho:** M

**Acceptance criteria:**
- **Given** uma relação configurada entre duas competências, **When** o sistema exibir uma competência relacionada inferida, **Then** mostra a origem da relação, a confiança e o rótulo de inferência, sem substituir o nível comprovado da pessoa.
- **Given** nenhuma relação ou evidência suficiente, **When** consultar a aderência a uma competência, **Then** o sistema não apresenta um nível inferido como fato e informa a ausência de evidência.

## Epic 2 — Demandas e simulação de cenários futuros

Objetivo: permitir que o coordenador modele a demanda por projeto e compare situações futuras sem alterar os dados confirmados do cenário-base.

### Task 2.1 — Modelar demandas e horizonte de planejamento

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um projeto e um horizonte de planejamento, **When** o usuário informar competências requeridas, níveis, período e carga, **Then** o sistema valida os campos obrigatórios e apresenta a demanda de forma editável.
- **Given** uma demanda incompleta ou sem período válido, **When** o usuário tentar salvá-la, **Then** o sistema identifica os campos inválidos e não a usa silenciosamente na otimização.

### Task 2.2 — Criar e comparar cenários

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um cenário-base, **When** o usuário criar um cenário alternativo com mudança de demanda, disponibilidade ou saída de especialista, **Then** o sistema preserva o cenário-base e registra as diferenças do cenário alternativo.
- **Given** dois ou mais cenários válidos, **When** o usuário compará-los, **Then** as premissas e os dados alterados são visíveis junto aos resultados, e cenários com dados insuficientes são sinalizados.

## Epic 3 — Alternativas multiobjetivo para desenvolvimento e alocação

Objetivo: gerar alternativas viáveis e comparáveis que explicitem conflitos entre objetivos, sem declarar uma alternativa universalmente ótima.

### Task 3.1 — Gerar alternativas de alocação, capacitação e mentoria

**Prioridade:** Must  
**Tamanho:** L

**Acceptance criteria:**
- **Given** dados válidos de competências, disponibilidade e demanda, **When** o usuário solicitar alternativas, **Then** o sistema retorna mais de uma estratégia viável quando houver soluções distintas, e cada estratégia identifica alocação, treinamento, mentoria ou rotação propostos.
- **Given** restrições incompatíveis ou ausência de solução viável, **When** a otimização terminar, **Then** o sistema informa a inviabilidade e as restrições conflitantes conhecidas, sem apresentar uma proposta inválida como recomendação.

### Task 3.2 — Comparar objetivos e trade-offs da fronteira de Pareto

**Prioridade:** Must  
**Tamanho:** L

**Acceptance criteria:**
- **Given** alternativas não dominadas, **When** o usuário abrir a comparação, **Then** pode comparar cobertura de competências, desenvolvimento, aderência a interesses, carga, risco de dependência, custo e estabilidade, conforme os dados disponíveis.
- **Given** uma métrica sem dados suficientes ou uma alternativa que melhora um objetivo e piora outro, **When** os resultados forem apresentados, **Then** a limitação ou o trade-off é visível e o sistema não reduz silenciosamente a comparação a um único score.

### Task 3.3 — Respeitar carga e restrições declaradas

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** limites de disponibilidade e carga declarados, **When** uma estratégia for avaliada, **Then** violações são rejeitadas ou destacadas conforme a regra configurada e não são ocultadas por uma pontuação agregada.
- **Given** as mesmas entradas, restrições e configuração do algoritmo, **When** a execução for repetida, **Then** a configuração usada e informação suficiente para reproduzir ou auditar o resultado ficam registradas.

## Epic 4 — Dashboard explicável e apoio à decisão humana

Objetivo: tornar alternativas, dados de origem, incertezas e limitações compreensíveis para uma discussão de planejamento.

### Task 4.1 — Visualizar competências, lacunas e riscos

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um cenário com competências e demandas, **When** o gestor abrir o mapa de competências, **Then** consegue distinguir níveis confirmados, inferências, evidências ausentes e demandas não cobertas.
- **Given** uma competência crítica coberta por poucas pessoas, **When** o painel de risco for exibido, **Then** apresenta o cálculo e as pessoas/competências que contribuem para o indicador, respeitando as permissões de acesso.

### Task 4.2 — Explicar e comparar alternativas

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** uma alternativa selecionada, **When** o usuário solicitar sua explicação, **Then** o sistema apresenta métricas, premissas, evidências e mudanças que justificam seus trade-offs, distinguindo cálculo determinístico de texto explicativo gerado por LLM.
- **Given** uma explicação gerada, **When** faltarem dados ou a justificativa não puder ser vinculada aos resultados, **Then** a incerteza é declarada e nenhuma alegação factual sem suporte é apresentada como evidência.

### Task 4.3 — Proteger dados e manter supervisão humana

**Prioridade:** Must  
**Tamanho:** M

**Acceptance criteria:**
- **Given** um usuário sem permissão para visualizar dados pessoais de uma pessoa, **When** acessar telas ou exportações do sistema, **Then** os dados protegidos não são expostos e o acesso negado não revela o conteúdo.
- **Given** qualquer alternativa produzida, **When** o gestor a consultar, **Then** o sistema a apresenta como apoio à decisão, exige avaliação humana antes de uso operacional e não executa alocação ou decisão de carreira automaticamente.

**Requisitos não funcionais**

- **Privacidade e segurança:** minimizar dados pessoais; restringir acesso por função; registrar acessos e alterações relevantes; proteger dados em trânsito e em repouso conforme a política do ambiente; permitir correção e remoção conforme governança definida antes do uso real.
- **Transparência:** mostrar origem, data, confiança e estado de revisão de dados; diferenciar observação, inferência e recomendação; disponibilizar premissas, objetivos e restrições considerados.
- **Confiabilidade:** validar entradas e restrições; indicar falhas ou ausência de solução sem fabricar resultados; registrar configuração e versão dos dados usadas em cada execução.
- **Usabilidade e acessibilidade:** permitir comparar cenários e alternativas sem depender exclusivamente de cor; apresentar definições das métricas e linguagem adequada a gestores e participantes.
- **Desempenho:** estabelecer metas após medir o volume esperado de pessoas, competências, projetos e alternativas no piloto; o MVP deve comunicar progresso e permitir cancelamento de execuções longas.

**Fora de escopo do MVP**

- Conectores automáticos para Jira, Azure DevOps, RH, transcrições, e-mail ou repositórios.
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