<!-- agent-graph-flow:start -->
## agent-graph-flow (`agf`) — src-gestor-equipes

Este projeto usa **agent-graph-flow** para gestão de execução via grafo persistente (SQLite).
Dados em `workflow-graph/graph.db` (local, gitignored). **Tudo via o CLI `agf` — zero MCP.**

### ⚠️ Regra de Execução OBRIGATÓRIA

**O grafo (`agf`) é a fonte de verdade ABSOLUTA. Nenhuma implementação acontece fora do grafo.**

1. **Node deve existir** — antes de escrever QUALQUER código, o node correspondente DEVE existir no grafo (`agf node add` ou `agf import-prd`).
2. **Fluxo obrigatório** — `agf start → [implementar com TDD] → agf done` (pipeline) ou `agf next → agf context <id> → [TDD] → agf check <id> → agf node status <id> done` (granular) — SEM EXCEÇÕES.
3. **Epic = estrutura primeiro** — `agf import-prd` (ou `agf node add` + `agf edge add`) cria Epic + tasks + edges ANTES de implementar.
4. **Status tracking** — `agf node status <id> in_progress` ANTES de codar, `agf node status <id> done` (ou `agf done <id>`) APÓS completar.
5. **Validação** — `agf check <id>` (DoD + AC + TDD) após cada task.
6. **Zero trabalho não-rastreado** — se não tem node no grafo, CRIAR PRIMEIRO.

> **Sem node no grafo = sem código escrito. Tudo via `agf` — zero MCP.**

### Comandos `agf` (CLI nativo — exponha 100%, zero MCP)

#### Front door (SHAPE → BUILD → SHIP)

| Comando | O que faz |
|---------|-----------|
| `agf deliver "<pedido>"` | Pipeline ponta-a-ponta: normaliza → PRD → grafo → build TDD |
| `agf import-prd <file> [--build-tree]` | Importa PRD (.md/.txt/.pdf/.html/.docx) → grafo |
| `agf generate-prd "<ideia>"` | Gera PRD a partir de um prompt (via LLM) |
| `agf build` | Lifecycle completo: PRD → grafo → decompose → autopilot |
| `agf autopilot [--simulate|--live|--max <n>|--retries <n>|--gate-gaps|--heal-on-fail]` | Loop autônomo: next → DoD → done|escalate |
| `agf loop --every <dur> <cmd> | --goal <rubric> --cmd <cmd>` | Loop por intervalo (--every) ou goal-driven (--goal) |
| `agf run "<prompt>"` | Execução one-shot: gera → aplica → testa |
| `agf exec` | Composição cross-platform de comandos agf |
| `agf exec pipe <command> [args...]` | Executa um comando agf e retorna o .data JSON |
| `agf exec chain "<cmd1>; <cmd2>; ..."` | Pipeline de comandos agf separados por ; |

#### Grafo — leitura

| Comando | O que faz |
|---------|-----------|
| `agf next` | Puxa a próxima task desbloqueada (pull, WIP=1) |
| `agf query [--type --status --parent --search --limit]` | Consulta nós por tipo/status/parent/texto |
| `agf node show <id>` | Detalhes de um nó + arestas de entrada/saída |
| `agf edge ls [--from <id>] [--to <id>]` | Lista arestas com filtros opcionais |
| `agf context <id> [--compressed]` | Context-pack compacto + RAG de um nó |
| `agf brief <id> [--format markdown|json|claude-prompt]` | Brief de execução p/ delegar ao executor |
| `agf search "<query>" [--limit <n>] [--hierarchical]` | Busca FTS5/BM25 sobre os nós do grafo (+ --hierarchical: navega o índice ToC-tree) |
| `agf retrieve-command "<intenção>" [--threshold <n>] [--limit <n>] [--local]` | RAG-IN: recupera o comando exato para uma intenção (fallback --help sob o limiar) |
| `agf montar-output "<objetivo>" [--threshold <n>] [--limit <n>]` | RAG-OUT: recupera scaffold adequado (preenche slots) ou gera, por objetivo |
| `agf stats` | Contagens e estatísticas: nodes, edges, byType, byStatus |
| `agf kanban [--swimlane]` | Board Kanban com swimlanes e métricas de fluxo |
| `agf insights` | Analítica determinística: DORA, gargalos, fases, fluxo |
| `agf insights dora` | Métricas DORA (deploy freq, lead time, CFR, MTTR, trend) |
| `agf insights bottlenecks` | Detecção de gargalos (bloqueadas, sem AC, oversized) |
| `agf insights phases` | Distribuição de tasks por fase do lifecycle |
| `agf insights wip` | Contagem de WIP + alerta de violação |
| `agf insights summary` | Resumo de fluxo: métricas + WIP + gargalos |
| `agf export [-o <file>]` | Serializa o grafo como JSON |

#### Grafo — mutação

| Comando | O que faz |
|---------|-----------|
| `agf node add --title <t> --type <t> [--parent <id> --status <s> --priority <n> --ac <c>]` | Cria um nó (task, epic, subtask, risk, etc.) |
| `agf node update <id> [--title --description --priority --type]` | Atualiza título, descrição, prioridade, tipo |
| `agf node status <id> <state> [--force]` | Muda status com validação status_flow |
| `agf node move <id> --parent <pid>` | Reparenta um nó sob novo pai |
| `agf node clone <id> [--parent <pid>]` | Clona um nó com seus atributos |
| `agf node rm <id>` | Remove um nó do grafo |
| `agf edge add <from> <to> [--type <t>] [--reason <r>]` | Cria relação (depends_on, blocks, parent_of…) |
| `agf edge rm <id>` | Remove uma aresta |
| `agf import-graph <file> [--dry-run]` | Funde um grafo JSON exportado no projeto |

#### Pipeline de task (2 calls)

| Comando | O que faz |
|---------|-----------|
| `agf start` | Inicia próxima task: wake-up + next + context + marca in_progress |
| `agf check <id>` | Definition of Done (12 checks) + aderência TDD |
| `agf done <id> [--skip-test]` | Finaliza: DoD + run tests + memória + done + sugere próxima |
| `agf pipeline` | Compound commands: múltiplas operações num único ciclo store |
| `agf pipeline next-context [--full] [-d dir]` | Find next task + load context (1 store open) |
| `agf pipeline next-start [--full] [-d dir]` | Find next + context + mark in_progress (1 store open) |
| `agf pipeline next-context-start [--full] [-d dir]` | Alias for next-start |

#### Decomposição & planejamento

| Comando | O que faz |
|---------|-----------|
| `agf decompose` | Detecta tasks grandes e sugere subtasks atômicas |
| `agf phase` | Taxonomia SHAPE→BUILD→SHIP + fase atual |
| `agf gate <design|review|handoff|deploy|listening|all>` | Gates de prontidão por fase do lifecycle |
| `agf template list` | Lista templates de decomposição disponíveis |
| `agf template apply <name>` | Aplica um template a um nó do grafo |
| `agf scaffold <nome> [--type class|fn|comp|iface|type]` | Scaffold/boilerplate determinístico (acoplador) |

#### Qualidade, harness, forecast

| Comando | O que faz |
|---------|-----------|
| `agf eval [--suite --models --provider --live --repeat --out]` | Suíte de cenários reais → scorecard |
| `agf harness [--violations]` | Scan de agent-readiness (8 dimensões, score A/B/C/D) |
| `agf swarm` | Coordenação multi-agente sobre o grafo (sessão/claim/mailbox/consensus) — opt-in |
| `agf swarm init --topology <t> --consensus <c> [--max <n>]` | Cria uma sessão de swarm (pending) |
| `agf swarm claim <resource> --agent <id> [--ttl <s>]` | Reivindica um recurso (lease+TTL) — exclusão mútua entre agentes |
| `agf swarm send --from <id> --to <id> --body <json>` | Courier agente-a-agente (send/recv/ack sobre a2a_mailbox) |
| `agf swarm consensus --votes <json>` | Consolida votos por maioria simples (floor(N/2)+1) |
| `agf provenance` | Escada epistêmica (claim→cited→validated→proven): gates de honestidade, local |
| `agf provenance promote --node <id> --to <tier> [--citation|--test-run|--receipt]` | Valida a evidência exigida para promover um node a um tier |
| `agf provenance downgrade --node <id> --from <tier> --test-run <id> --cause <text>` | Reverte o tier quando a evidência cai (forget-gate) |
| `agf provenance hash [--content <s>|--file <p>]` | Recibo determinístico local (sha256 canônico) — habilita o tier proven sem rede |
| `agf hooks` | Inspeciona a taxonomia de 28 hooks (list/test/discover) |
| `agf hooks list` | Lista os 28 pontos: ponto → canal → módulo-owner |
| `agf hooks test <channel>` | Dry-fire de um canal com payload de fixture |
| `agf hooks discover` | Lista canais da taxonomia sem handler registrado |
| `agf code index` | Re-indexa o projeto (tree-sitter + LSP) |
| `agf code search <symbol>` | Busca semântica de símbolos via FTS5 |
| `agf code callers <symbol>` | Lista callers de um símbolo (incoming calls) |
| `agf code callees <symbol>` | Lista símbolos chamados (outgoing calls) |
| `agf code def <symbol>` | Go-to-definition via LSP |
| `agf code refs <symbol>` | Lista todas as referências via LSP |
| `agf code impact <file>` | Blast radius: símbolos afetados por mudança |
| `agf code affected <file>` | Testes afetados por mudanças no arquivo |
| `agf gaps [--kind --severity --limit --json]` | Detecta lacunas de completude (~0 token) |
| `agf scan-repos [root] [--report --ingest --json]` | Explora repos vizinhos: fingerprint + insights |
| `agf quality` | Gate 95/95 (testes + logs sobre src/) |
| `agf forecast` | Previsão de ETA do backlog com 95% CI |

#### Memória, snapshot, heal

| Comando | O que faz |
|---------|-----------|
| `agf memory write <name> [--content <c>|--file <f>]` | Escreve uma memória do projeto |
| `agf memory read <name>` | Lê uma memória do projeto |
| `agf memory list` | Lista todas as memórias do projeto |
| `agf memory rm <name>` | Remove uma memória do projeto |
| `agf memory search "<query>" [--limit <n>]` | Busca textual nas memórias do projeto |
| `agf snapshot create` | Cria um snapshot do grafo (backup) |
| `agf snapshot list` | Lista snapshots disponíveis |
| `agf snapshot restore <id>` | Restaura o grafo a partir de um snapshot |
| `agf heal [--apply] [--log]` | Self-healing do grafo (MAPE-K) |
| `agf gc` | Coleta de lixo (worktrees/branches órfãos) |

#### Modelo, métricas, custo

| Comando | O que faz |
|---------|-----------|
| `agf calibrate [--lever <name>] [--band <n>]` | Calibra o limiar do portão RAG por score×saved (lê o lever ledger) |
| `agf model list` | Lista tiers do tier-router (cheap/build/frontier/fallback) |
| `agf model current` | Mostra o modelo ativo configurado |
| `agf model set <id|auto>` | Fixa um modelo ou volta para auto |
| `agf model route <kind>` | Mostra qual modelo o tier-router usaria |
| `agf provider list` | Lista providers LLM disponíveis |
| `agf provider use <id> [--base-url <url>]` | Seleciona o provider ativo |
| `agf provider current` | Mostra provider ativo + fallback chain |
| `agf provider set-url [url]` | Define/limpa o endpoint do provider ativo |
| `agf provider failover [chain] [--clear]` | Configura cadeia de failover |
| `agf metrics [--session --baseline --simulate --economy-report]` | Tokens/$ por task e sessão (llm_call_ledger) |
| `agf compress <filters|discover|test>` | Compressor de saída de ferramenta |
| `agf compress filters` | Lista filtros de compressão ativos |
| `agf compress discover [--ledger]` | Saídas sem filtro registradas |
| `agf compress test <file>` | Testa qual filtro casaria com um arquivo |
| `agf rtk <filters|discover|test>` | Alias para agf compress |
| `agf savings [--reset]` | Economia cumulativa de tokens (ledger) |
| `agf retrieve <hash> [--query --limit]` | Resgata original CCR por hash |
| `agf learning stats` | Performance por-agente + routing |
| `agf learning route <agentId>` | Decisão de roteamento de agente baseada no histórico |
| `agf learning explain <agentId>` | Explica a decisão de roteamento (breakdown) |
| `agf learning export` | Exporta todos os registros de learning (JSON) |
| `agf status` | Painel unificado: provider/model/cache + tokens/$ |

#### Spec-kit & governança

| Comando | O que faz |
|---------|-----------|
| `agf adr create` | Cria um Architecture Decision Record no grafo |
| `agf adr list` | Lista ADRs existentes no grafo |
| `agf constitution` | Princípios governantes: --create|--list|--check |
| `agf preset --list|--show|--apply <name>` | Presets de workflow: --list|--show|--apply |
| `agf spec --generate|--validate|--list-templates` | Geração/validação de specs por fase |
| `agf spec-sync register` | Registra uma spec versionada |
| `agf spec-sync list` | Lista specs registradas |
| `agf spec-sync status` | Status de sync das specs |
| `agf spec-sync link <specId> <nodeId>` | Linka spec a um nó do grafo |
| `agf principles` | Doctrine: lista e exibe princípios |
| `agf plugin` | Gerencia plugins (--install, --remove, --list) |
| `agf profile` | Perfis de configuração (list, show) |

#### Dev tooling (test, lint, usage)

| Comando | O que faz |
|---------|-----------|
| `agf test [--blast|--changed|--file <path>|--node <id>]` | Vitest: --blast|--changed|--file|--node |
| `agf lint [--fix|--file <path>|--all]` | ESLint: --fix|--file|--all |
| `agf usage report [--top <n>]` | Top comandos usados + sugestão de wrappers |
| `agf usage wrap <command> [--apply]` | Auto-gera wrapper agf para comando nativo |

#### Setup & ambiente

| Comando | O que faz |
|---------|-----------|
| `agf init` | Inicializa o projeto: DB, gitignore, context files, docs |
| `agf doctor [--json --providers]` | Diagnóstico do ambiente + contexto LLM + drift detection |
| `agf daemon start [-p <port>]` | Inicia o serviço local em background |
| `agf daemon stop` | Para o serviço local deste workspace |
| `agf daemon status` | Verifica se o daemon está rodando |
| `agf daemon prune [--dry-run]` | Mata daemons órfãos + limpa state dirs |
| `agf daemon list` | Lista daemons e seus status |
| `agf login` | Autentica no GitHub Copilot (device-flow) |
| `agf logout` | Remove o token do GitHub Copilot |
| `agf skill list` | Lista skills do ciclo de vida |
| `agf skill show <name>` | Exibe o conteúdo de uma skill |
| `agf tui` | TUI interativa (Ink) — agf sem args num TTY |
| `agf ui [--port <n>]` | Web mínima de progresso: grafo + tokens + logs |

> Dev: `npm run dev -- <comando>`. Build: `agf` (binário) ou `agent-graph-flow`.
> `agf` sem args num TTY (com projeto) abre a TUI.

### Custo de token & providers (3º pilar)

**Providers** — `agf provider use <id>` escolhe por onde a chamada LLM vai. A *mesma* via CLI serve qualquer agente (Claude, Copilot, Codex, Cursor, Gemini…) — **nunca MCP**.
Todos os 10 providers são auto-detectados de env vars (`agf doctor --providers` lista quais estão configurados):

| Provider | Env var | Gateway |
|----------|---------|---------|
| `anthropic` | `ANTHROPIC_API_KEY` | auto-wired |
| `openai` | `OPENAI_API_KEY` | auto-wired |
| `openrouter` | `OPENROUTER_API_KEY` | auto-wired |
| `gemini` | `GEMINI_API_KEY` | auto-wired |
| `bedrock` | `BEDROCK_API_KEY` | auto-wired |
| `azure` | `AZURE_OPENAI_API_KEY` | auto-wired |
| `deepseek` | `DEEPSEEK_API_KEY` | auto-wired |
| `glm` | `GLM_API_KEY` | auto-wired |
| `kimi` | `KIMI_API_KEY` | auto-wired |
| `groq` | `GROQ_API_KEY` | auto-wired |
| `copilot` | (via `agf login`) | default |
| `ollama` | (local, $0/token) | manual URL |

- **OpenRouter:** `export OPENROUTER_API_KEY=…` → `agf provider use openrouter`. Fixe um modelo com `--pin` (ex.: `agf deliver "…" --live --pin deepseek/deepseek-v4-flash`) ou deixe o tier-router escolher (cheap→`deepseek-v4-flash`, build→`llama-4-maverick`, frontier→`qwen3.6-plus`).

**Alavancas automáticas** (sem comando — agem no gateway): diff-edits (só a região alterada), repo-map ranqueado por PageRank (~1k tok), lossy-gate (auto-revert se a compressão quebra o sentido), AAAK, content-router (SmartCrusher p/ arrays JSON homogêneos + compressão AST de código), **CCR reversível** (cacheia o original + marcador ⟨ccr:hash⟩ → outcome `ccr_dropped`; resgate com `agf retrieve <hash>`), retry com feedback compacto. Cada economia entra no `llm_call_ledger`.

**Medir** (transformar a promessa em número):
- `agf metrics [--economy-report]` — tokens/$ por task e sessão + o que as alavancas pouparam.
- `agf metrics --simulate` — re-precifica a fatura real sob todos os modelos.
- `agf eval --models <ids> --live` — cenários reais → scorecard (resolve% × custo-por-sucesso).
- `agf savings` — economia cumulativa de tokens por task (ledger real, cached tokens contabilizados automaticamente).
- `agf savings --reset` — zera o contador cumulativo.

**Alavancas bio/matemáticas (opt-in)** — `agf economy list` lista cada lever com o flag `enabled` + tokens `saved` cumulativos (JSON `--select data.levers`); `agf economy on <lever>` / `agf economy off <lever>` ligam/desligam. Default tudo OFF → comportamento byte-idêntico. Levers fundamentados em papers/biologia: `memory_salience` (ACT-R), `ncd_dedup` (Kolmogorov/NCD), `forage_stop` (MVT de Charnov), `budget_kleiber` (lei de Kleiber 3/4), `heat_kernel` (difusão `e^{-tL}`), `mdl_select` (MDL de Rissanen). Cada economia entra no `economy_lever_ledger` e aparece em `agf metrics --select data.levers`.

**Rastreabilidade** — cada chamada LLM é gravada no `llm_call_ledger` com `node_id` (atribuição por task), `cached_input_tokens`, `cost_usd` e `session_id`. O `agf done` registra automaticamente a economia da task. Use `agf doctor --providers` para ver quais providers estão configurados no ambiente.

### Harness de Completude — `agf gaps` (detect → delegate → verify)

`agf gaps` é determinístico (~0 token) e acha lacunas de completude no grafo: rastreabilidade
requirement→task→test, cobertura de AC na decomposição, AC sem testabilidade, NFR faltando,
edge-cases/erros ausentes, ambiguidade, atomicidade, design/estimate drift.

**A IA condutora (você — Copilot/Claude/Codex/Cursor/Gemini/OpenCode) fecha as lacunas**; o agf só
detecta e re-verifica. Cada gap traz `applyVia`: os comandos `agf` exatos pra fechá-lo.

**Loop:**
1. `agf gaps --severity required --json` — pega os blockers acionáveis.
2. Pra cada gap, rode o `applyVia` (ex.: `agf edge add --from <task> --to <req> --type implements`), escolhendo a semântica.
3. `agf gaps` de novo até `ready: true` — desfecho determinístico, independente de qual CLI fechou.

Filtros: `--kind <k>`, `--severity required|recommended`, `--limit N`, `--json` (relatório completo p/ loops).

### Brief de execução — delegando uma task ao executor

**Heurística:** _especifique a ponta e a saída; delegue o meio._ Onde o executor pode errar caro
(contrato, limites, incerteza) você gasta tokens preventivos baratos; o que ele faz bem sozinho
(escrever o código dentro das guardas) você deixa livre. "De outro mundo" não é um prompt mais longo —
é um que fecha as saídas de erro caras com o mínimo de palavras.

Gere o esqueleto pronto a partir do node: `agf brief <id>` (`--format markdown|json|claude-prompt`).
Ele auto-preenche o que o grafo sabe (intenção, AC, blast radius, deps, prontidão) e deixa os campos
de julgamento como `<fill: …>` pra você completar.

**Template:**
- **Intenção** (1 linha): para que existe / efeito desejado.
- **Tarefa** (atômica): uma só — node do grafo: `<id>`.
- **Imite:** arquivo-espelho a seguir como padrão.
- **Ler/tocar** (exato): caminhos + símbolos a reusar.
- **Contrato:** assinatura/tipos/comportamento (trechos pequenos **inline**; arquivos grandes → aponte o path).
- **AC** (testável): 2–4 critérios verificáveis.
- **NÃO:** refatorar vizinhos / deps novas / tocar X / mudar default.
- **Blast radius:** arquivos sensíveis → mudança aditiva.
- **Orçamento:** ~N arquivos, sem deps, sem hot-path.
- **Incerteza:** se o contrato falhar ou faltar info, PARE e reporte; se ambíguo, escolha e justifique em 1 linha.
- **Teste com:** fixture/stub concreto (ex.: `new Database(':memory:')`, stub da chamada LLM com contador) — evita setup flaky ou bater em auth que não existe no sandbox.
- **DoD:** typecheck · teste do arquivo · blast · lint.
- **Self-review antes de retornar** (~30 tokens, substitui um ciclo caro): sobrou placeholder? escopo vazou? AC cobertos? default intacto?
- **Retorne (schema):** `{arquivos[], testes{passed,failed}, desvios[]}` — sem dump de código; não commitar.

**Validação de retorno** — o condutor usa `parseExecutorResult(resposta)` para parsear o JSON estruturado
do executor (com fallback regex) e `validateBriefReady(brief)` para verificar que todos os campos de
julgamento (`imitate`, `readTouch`, `contract`, `testWith`) foram preenchidos antes de delegar.
Retorno inválido → rejeitar e pedir correção; válido → fechar o loop em 1 passo.

> Retorno estruturado torna a validação trivial (parse em vez de leitura). O condutor valida e fecha o loop; o executor escreve o meio.

### Fluxo de trabalho OBRIGATÓRIO

**Pipeline (2 calls):**
```bash
agf start                 # wake-up + next + context + marca in_progress
# … implementa com TDD (Red → Green → Refactor) …
agf done <id>             # DoD + memória + marca done + sugere próxima
```

**Granular (controle fino):**
```bash
agf next                  # puxa a próxima task (pull, WIP=1)
agf context <id>          # context-pack compact + RAG
# … TDD …
agf check <id>            # Definition of Done + aderência TDD
agf node status <id> done # transição validada (status_flow)
```

**Modo delegado (sem provider — qualquer CLI-agente dirige):** se nenhum provider
está conectado ao agf, os comandos `--live` (`agf run`/`agf deliver`/`agf autopilot --live`)
NÃO quebram — retornam `mode:delegated` com o brief pronto p/ VOCÊ (Claude/Copilot/Codex/…)
executar com seu próprio LLM. Feche o loop com `agf submit`:
```bash
agf next                  # próxima task
agf brief <id>            # spec de delegação (intenção, AC, contrato, blast)
# … você implementa com seu próprio LLM e aplica os edits …
agf submit <id> --result '{"arquivos":["x.ts"],"testes":{"passed":N,"failed":0},"desvios":[]}'
                          # valida → blast → DoD → done; desvios viram findings
```

### Lifecycle (9 fases) — comandos `agf` por fase

1. **ANALYZE** — `agf import-prd` · `agf node add` · `agf gate` (Definition of Ready)
2. **DESIGN** — `agf node add`/`agf edge add` (ADRs, interfaces) · `agf constitution` · `agf gate design`
3. **PLAN** — `agf decompose` · `agf template apply` · AC testável por task
4. **IMPLEMENT** — `agf start` → TDD → `agf done` (ou granular) · `agf harness`
5. **VALIDATE** — `agf check <id>` · `agf gate` · `agf metrics`
6. **REVIEW** — `agf export` · `agf insights` · `agf gate review`
7. **HANDOFF** — `agf memory write` · `agf snapshot create` · `agf gate handoff`
8. **DEPLOY** — `agf export` · `agf forecast` · `agf gate deploy` (harness ≥ 70)
9. **LISTENING** — `agf node add` · `agf import-prd` (novo ciclo)

### Índice de skills do ciclo (escolha a abordagem certa)

Qualquer CLI lê esta tabela pra escolher a skill certa pro intent atual — a coluna **Quando usar** mapeia situação → skill. Rode com `agf skill show <name>` ou siga o comando de entrada.

| Skill | Fase | Quando usar | Comando de entrada | Skills relacionadas |
|-------|------|-------------|--------------------|---------------------|
| `graph-prd` | ANALYZE | Start of a cycle with a vague idea | `agf generate-prd "<idea>"` | graph-analyze |
| `graph-analyze` | ANALYZE | PRD already imported | `agf import-prd <file>` | graph-prd, graph-design |
| `graph-design` | DESIGN | DoR approved | `agf context <id>` | graph-analyze, graph-plan |
| `graph-plan` | PLAN | DESIGN ready | `agf context <id>` | graph-design, graph-implement |
| `graph-implement` | IMPLEMENT | An unblocked task exists | `agf start` | graph-plan, graph-validate, graph-bugs |
| `graph-validate` | VALIDATE | ≥50% of tasks done with AC | `agf kanban` | graph-implement, graph-review |
| `graph-review` | REVIEW | VALIDATE complete | `agf insights` | graph-validate, graph-handoff |
| `graph-handoff` | HANDOFF | REVIEW approved | `agf memory write <name>` | graph-review, graph-deploy |
| `graph-deploy` | DEPLOY | HANDOFF approved | `agf provider use <id>` | graph-handoff, graph-listening |
| `graph-listening` | LISTENING | Post-deploy | `agf learning stats` | graph-deploy, graph-analyze |
| `graph-quality` | REVIEW | Code smells or accumulated debt | `agf quality` | graph-review, graph-validate |
| `graph-security` | REVIEW | Change touches authn/authz, external I/O or secrets | `agf check <id>` | graph-review, graph-deploy |
| `graph-bugs` | IMPLEMENT | Incorrect behavior observed | `agf node add --type bug` | graph-implement |
| `graph-platform` | VALIDATE | Delivery has a UI/platform surface | `agf harness` | graph-validate, graph-deploy |
| `graph-mega-brain` | ORCHESTRATION | Drive a PRD/feature end-to-end through the graph (ANALYZE→…→LISTENING) | `agf stats / agf query` | graph-lead, graph-implement, graph-validate |
| `graph-economy` | OPTIMIZE | Token cost matters and you want deterministic, opt-in input cuts beyond the always-on RAG/repo-map | `agf economy list` | graph-mega-brain, graph-implement, graph-deploy |

### Definition of Done (rode `agf check <id>` antes de `agf done`)

| # | Check | Severidade |
|---|-------|------------|
| 1 | Tem acceptance criteria | required |
| 2 | Score AC ≥ 60 (INVEST) | required |
| 3 | Sem blockers não resolvidos | required |
| 4 | Status flow válido (passou por in_progress) | required |
| 5 | Tem descrição | recomendado |
| 6 | Não oversized (sem L/XL sem subtasks) | recomendado |
| 7 | ≥1 AC testável | recomendado |
| 8 | testFiles preenchido | recomendado |

### Princípios de Fluxo (Little's Law + Lean + TOC)

- **WIP = 1** — no máximo 1 task `in_progress`. `cycle_time = WIP / throughput`.
- **Pull, não Push** — `agf next` puxa; nunca empurrar para in_progress sem terminar a anterior.
- **Gargalo primeiro (TOC)** — se VALIDATE acumula, pare de implementar e valide.
- **Eliminar desperdício (Lean/Toyota)** — sem overproduction (features não planejadas), sem waiting (tasks blocked sem ação), use `agf context` (não dumps), TDD elimina defects.
- **Métricas de fluxo** — `agf insights` / `agf forecast`: cycle time, lead time, throughput, flow efficiency (> 40%).

### Princípios XP Anti-Vibe-Coding

- **TDD obrigatório** — Teste antes do código. Sem teste = sem implementação.
- **Anti-one-shot** — Nunca gere sistemas inteiros em um prompt. Decomponha em tasks atômicas (`agf decompose`).
- **Decomposição atômica** — Cada task completável em ≤2h.
- **Honestidade** — surfar pontas soltas como finding/risk no grafo (`agf node add --type risk`); nunca marcar done com alegação falsa.
- **CLAUDE.md como spec evolutiva** — documente padrões e decisões.

### Gates de Teste Hierárquicos

| Gate | Comando | Trigger |
|------|---------|---------|
| Task | `npm run test:blast` | a cada task finalizada (`agf done`) |
| Épico | `npm run test:node` | promoção de épico |
| PR | `npm test` | antes de push/PR |

Blast obrigatório no `agf done`. Full obrigatório pré-PR.

### Spec-Driven Development (spec-kit, via `agf`)

- `agf constitution` — princípios governantes (indexados, validados em gates).
- `agf preset --apply <name>` — workflow (default/strict-tdd/agile-light/enterprise).
- `agf spec --generate <template>` / `--validate <file>` — specs por fase.
- `agf spec-sync link <specId> <nodeId>` — specs vivas ligadas ao grafo.

### Memory ≠ Estado Atual

Memory files são snapshots point-in-time, não estado live. Contagens ("X/Y done") ficam stale.

1. Grep pelo arquivo/função — se existe, o memory é stale.
2. **Código vence memory.**
3. Reconcilie com `agf stats`/`agf query` antes de planejar.

> Nunca confiar em contagens de progresso de memories. Verificar no código/grafo primeiro.

> **Referência completa de comandos:** `agf help` (índice agrupado) · `agf <comando> --help` (flags) · `agf skill list` (skills do ciclo de vida).
<!-- agent-graph-flow:end -->
