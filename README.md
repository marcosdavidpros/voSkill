# NorteiaSkills

O NorteiaSkills apoia o planejamento de competências: permite analisar cobertura e riscos,
comparar cenários e examinar alternativas de otimização. Os resultados são apoio à
decisão e não aplicam uma alocação automaticamente.

## Desenvolvimento local

Requer Python 3.11 ou superior.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edite `.env` e preencha as configurações Oracle e de autenticação descritas abaixo. Use o formato Easy Connect para DSNs, por exemplo `//host:1521/service_name`. O arquivo `.env` é local e ignorado pelo Git; não coloque credenciais reais no `.env.example`.

Inicie a API com:

```powershell
python -m uvicorn voskill.main:app --reload --env-file .env
```

O endpoint `GET /health` não depende de conexão Oracle. A aplicação abre conexões somente quando uma operação de persistência solicitar.

Em outro terminal, instale e inicie o dashboard (requer Node.js e npm):

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Abra o endereço local mostrado pelo Vite. Em desenvolvimento, o frontend encaminha
as chamadas `/api` para `http://127.0.0.1:8000`. A documentação interativa da API
fica em `http://127.0.0.1:8000/docs`.

### Antes de usar o dashboard

1. Aplique as sete migrations Oracle descritas abaixo e configure a conexão no `.env`.
2. Providencie dados existentes de pessoas, skills, projeto e cenário-base com seu
	snapshot. A API atual oferece cadastro de competências e demandas e criação de
	cenários alternativos, mas não oferece endpoints para cadastrar pessoas, skills,
	projetos, snapshots ou cenários-base. A carga inicial desses dados depende de um
	administrador ou integração autorizada; não há seed automático incluído.
3. Configure LDAPS e acesso restrito ao Oracle do Portal conforme
	 **Autenticação corporativa**. O login só é aceito para matrícula ativa com perfil
	 ativo/não expirado e permissão `VOSKILL` habilitada.

### Autenticação corporativa

O NorteiaSkills autentica diretamente no diretório corporativo via LDAPS e consulta o
Oracle do Portal para autorização; não chama o Portal em runtime. A matrícula
normalizada em maiúsculas é o `actor_id` registrado nas operações.

A autorização consulta `PARAM_USUARIOS`, `PARAM_USUARIO_PERFIS`, `PARAM_PERFIS`,
`PARAM_PERFIL_TELAS` e `PARAM_TELAS`. A conta técnica também atualiza
`PARAM_USUARIOS.ULTIMO_LOGIN` após um login autorizado.

Há duas conexões Oracle distintas:

- `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`: schema do NorteiaSkills, com as migrations
	`VSK_*`.
- `PORTAL_ORACLE_USER`, `PORTAL_ORACLE_PASSWORD`, `PORTAL_ORACLE_DSN`: schema Portal,
	usado para validar `PARAM_USUARIOS`, perfis e a permissão da tela `VOSKILL`, além de
	atualizar `PARAM_USUARIOS.ULTIMO_LOGIN`. Use uma conta técnica dedicada com grants
	mínimos: leitura das tabelas de autorização e atualização apenas de `ULTIMO_LOGIN`.

Configure também:

- `LDAP_URL`: aceita `ldap://` e `ldaps://`. O Portal atualmente usa `ldap://`; nesse
	modo a senha trafega sem criptografia. Use-o somente numa rede confiável e isolada.
	Prefira `ldaps://host:636` quando o servidor suportar LDAPS.
- `LDAP_DOMAIN`: domínio/prefixo usado antes da matrícula, no formato do Portal, por
	exemplo `EMPRESA\`.
- `LDAP_TIMEOUT` e `LDAP_CONNECT_TIMEOUT`: timeouts em milissegundos, como no Portal;
	são convertidos para segundos para o cliente Python. O padrão é `10000` e os valores
	aceitos vão de `100` a `120000`.
- `LDAP_FOLLOW_REFERRALS`: `true` ou `false`; o padrão compatível com o exemplo do
	Portal é `false`.
- `LDAP_BASE_DN`: mantida no `.env.example` por paridade com o Portal. O login atual
	faz bind direto com domínio e matrícula, sem pesquisar entradas por base DN.
- `LDAP_CA_CERT`: usado com `ldaps://`; informe o caminho para a CA em PEM se ela não
	estiver na trust store do sistema. Com LDAPS, a validação do certificado continua
	obrigatória.
- `VOSKILL_SESSION_SECRET`: segredo aleatório com pelo menos 32 bytes para assinar
	cookies. Gere um valor novo por ambiente; não use o mesmo segredo em dev e produção.
- `VOSKILL_SESSION_MAX_AGE`: validade em segundos, de 60 a 86400; padrão `1800`.
- `VOSKILL_SESSION_COOKIE_SECURE`: padrão `1`, envia o cookie apenas por HTTPS/loopback
	seguro. Só use `0` em desenvolvimento isolado por HTTP.

Copie `.env.example` para `.env`, substitua todos os placeholders e mantenha o arquivo
fora do Git. Para gerar um segredo no PowerShell:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Depois de preencher as variáveis, reinicie a API e o frontend. Abra o dashboard e entre
com a matrícula e senha corporativas. `GET /auth/me` confirma a sessão; `POST
/auth/logout` encerra o cookie. O cookie é `HttpOnly`, `SameSite=Lax`, assinado e curto;
a senha não é guardada nele.

`PODE_VISUALIZAR` habilita leitura global dos dados do NorteiaSkills. `PODE_EDITAR` permite
alterações e implica leitura. Uma sessão ausente, inválida ou expirada retorna `401`;
um usuário sem acesso à tela `VOSKILL` recebe erro de autenticação; um usuário somente
de leitura recebe `403` em gravações. Erros `AUTHENTICATION_UNAVAILABLE` indicam
configuração incompleta ou indisponibilidade de LDAP/Oracle do Portal. Não habilite
modo local alternativo: o bypass anterior de competências foi removido.

### Usar o MVP

1. Em **Cobertura de competências**, informe o ID de um cenário existente e selecione
	**Carregar mapa**. A tela tenta abrir `S-001` inicialmente; esse ID é apenas um
	valor inicial, não um cenário criado automaticamente.
2. Consulte as skills **Confirmada**, **Inferida** e **Sem cobertura**, as evidências
	e a origem. Inferências são hipóteses e não contam como cobertura confirmada.
3. Em **Risco por limiar configurado**, selecione uma skill, informe o mínimo de pessoas
	confirmadas (inteiro maior ou igual a 1) e salve. O painel mostra skills abaixo do
	limiar. Alterar limiares exige autorização de projeto ou permissão específica.
4. Em **Comparação**, use a aba **Cenários**, informe dois IDs e compare as premissas
	por período, incluindo valores sem alteração e dados ausentes. O acesso exige
	autorização aos projetos ou às pessoas envolvidas, ou permissão global.
5. Para examinar otimizações, uma integração ou usuário autorizado deve primeiro criar
	uma execução em `POST /optimization-runs`, fornecendo o snapshot de otimização e
	a seed. Use o `run_id` e os IDs em `result.feasible_alternatives` da resposta para
	consultar **Explicação da alternativa** ou comparar duas alternativas na aba
	**Alternativas**. A tela apresenta métricas separadas, trade-offs, premissas da
	execução e restrições registradas; não cria execuções pela interface.

Um cenário incompleto informa os campos ausentes. A narrativa de explicação e a
extração de sugestões ficam indisponíveis com os provedores padrão atuais; isso não
deve ser interpretado como uma afirmação gerada. A aplicação de alternativas retorna
`HUMAN_APPROVAL_REQUIRED`: o MVP ainda não fornece um fluxo de aprovação e aplicação.

### Operações disponíveis pela API

Use a documentação interativa para consultar os campos, respostas e validações de cada
endpoint. Após configurar a identidade e os dados iniciais, o fluxo típico inclui:

| Operação | Endpoint |
| --- | --- |
| Cadastrar ou consultar competências de uma pessoa | `POST` / `GET /people/{person_id}/competencies` |
| Cadastrar ou consultar demandas de um projeto | `POST` / `GET /projects/{project_id}/demands` |
| Criar alternativa a partir de cenário-base | `POST /scenarios/{base_scenario_id}/alternatives` |
| Comparar cenários | `GET /scenarios/{first_scenario_id}/compare/{second_scenario_id}` |
| Executar e consultar otimização | `POST /optimization-runs` e `GET /optimization-runs/{run_id}` |
| Explicar ou comparar alternativas | `GET /optimization-runs/{run_id}/alternatives/{alternative_id}/explanation` e `POST /optimization-runs/{run_id}/alternatives/compare` |

Os snapshots de cenário usam `periods` com demanda e disponibilidade por mês; o
snapshot enviado à otimização é um contrato diferente, com `snapshot_id`, `profiles`
e `demands`. Não envie automaticamente um como se fosse o outro.

Exemplo de corpo para `POST /optimization-runs`, com dados fictícios:

```json
{
	"snapshot": {
		"snapshot_id": "S-001",
		"profiles": [
			{"person_id": "P-001", "competencies": {"SKILL-1": 4}, "availability": {"2026-01": 40}},
			{"person_id": "P-002", "competencies": {"SKILL-1": 2}, "availability": {"2026-01": 50}}
		],
		"demands": [
			{"demand_id": "D-001", "skill_id": "SKILL-1", "proficiency_level": 3, "period": "2026-01", "load_amount": 40}
		]
	},
	"seed": 42,
	"population_size": 20,
	"generations": 12
}
```

Substitua os identificadores e valores pelos dados autorizados do planejamento. A
disponibilidade é informada por pessoa e mês; o otimizador rejeita alocações sem
disponibilidade ou acima da capacidade. Guarde o `run_id` retornado e consulte os IDs
em `result.feasible_alternatives`; só é possível comparar alternativas existentes e
viáveis da mesma execução. A resposta pode não conter alternativas viáveis.

## Oracle

O script `database/oracle/001_initial_schema.sql` cria as tabelas de pessoas, skills, competências/histórico, projetos e demandas, além de índices, constraints e triggers de horizonte. Todos os objetos usam o prefixo `VSK_` para identificar o projeto e evitar colisões. Os identificadores são UUIDs gerados pela aplicação. Execute o script uma vez conectado como owner `ITB2CTRF`; o guard interrompe a execução para qualquer outro usuário, e o script não remove nem recria tabelas existentes.

Com SQL*Plus instalado, conecte-se ao serviço e execute as migrations em ordem:

```powershell
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/001_initial_schema.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/002_scenarios.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/003_competency_suggestions.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/004_suggestion_review.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/005_skill_relations.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/006_optimization_runs.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/007_critical_skill_thresholds.sql
```

`002_scenarios.sql` cria snapshots JSON imutáveis e cenários que compartilham o snapshot-base; overrides ficam separados em `DELTAS_JSON`. A migration aborta se os objetos já existirem, portanto não a reexecute após uma aplicação bem-sucedida.

`003_competency_suggestions.sql` cria a fila de revisão humana. A aplicação persiste somente o trecho exato de evidência e o SHA-256 da fonte, não o texto-fonte integral; sem extractor configurado, o endpoint retorna `PROVIDER_UNAVAILABLE`.

`004_suggestion_review.sql` adiciona os valores revisados e a referência opcional à competência confirmada. O endpoint `POST /people/{person_id}/competency-suggestions/{suggestion_id}/review` aceita `accept`, `edit` ou `reject`; somente requests autorizados pelo middleware atualizam o perfil, e a decisão e o histórico são gravados numa única transação.

`005_skill_relations.sql` cria relações direcionais entre skills, com FKs para origem e destino e confidence limitada a 0–1. O endpoint `POST /skill-relations` exige um ator autenticado com a claim `can_manage_skill_relations`; skills inexistentes e confidence inválida são rejeitadas sem persistência.

`006_optimization_runs.sql` cria o registro auditável de execuções, incluindo hash do snapshot, versão do pymoo, configuração, seed, hash canônico das alternativas, resultado, ator e timestamp. O endpoint autenticado `POST /optimization-runs` executa um snapshot e grava o run; `GET /optimization-runs/{run_id}` permite recuperá-lo ao ator que o criou. Seed negativa é rejeitada com `INVALID_SEED` antes de persistência.

`007_critical_skill_thresholds.sql` cria os limiares de pessoas confirmadas por
projeto e skill, usados pelo painel de risco.

### Tabelas do MVP

| Tabela | Finalidade |
| --- | --- |
| `VSK_PERSONS` | Cadastro de pessoas, nome de exibição e estado ativo. |
| `VSK_SKILLS` | Catálogo de skills com nome e descrição. |
| `VSK_PERSON_COMPETENCIES` | Competências confirmadas por pessoa e skill, com nível, evidência, origem e revisão. |
| `VSK_PERSON_COMPETENCY_HISTORY` | Histórico de alterações de nível e evidência das competências confirmadas. |
| `VSK_PROJECTS` | Projetos, horizonte de planejamento e unidade de carga. |
| `VSK_PROJECT_DEMANDS` | Demandas de skills por projeto e mês, nível exigido e carga. |
| `VSK_SCENARIO_SNAPSHOTS` | Dados JSON e hash do snapshot imutável usado como base dos cenários. |
| `VSK_SCENARIOS` | Cenários-base e alternativos, ligados ao projeto e snapshot; alternativas guardam seus deltas JSON. |
| `VSK_SKILL_SUGGESTIONS` | Sugestões de competências, evidência, hash da fonte e decisão de revisão humana. |
| `VSK_SKILL_RELATIONS` | Relações direcionais entre skills e confiança, usadas para inferir competências não confirmadas. |
| `VSK_OPTIMIZATION_RUNS` | Execuções de otimização, configuração, seed, hashes, resultado, ator e data para rastreabilidade. |
| `VSK_CRITICAL_SKILL_THRESHOLDS` | Mínimo de pessoas confirmadas por projeto e skill para identificar riscos de dependência. |

Pessoas e skills se relacionam por competências; projetos têm demandas e cenários;
cada cenário aponta para um snapshot. Execuções de otimização guardam o hash e os
resultados do snapshot enviado, sem chave estrangeira para a tabela de snapshots de
cenário. A migration 004 complementa `VSK_SKILL_SUGGESTIONS`, sem criar outra tabela.

O endpoint `GET /people/{person_id}/skill-inference/{target_skill_id}` exige autorização para consultar a pessoa. Ele retorna `inferred` somente quando existe uma relação ativa e a pessoa tem a competência-fonte confirmada; o nível inferido espelha o nível-fonte, e a relação ativa de maior confidence é escolhida primeiro. Sem evidência suficiente, retorna `insufficient_evidence` sem nível inferido. A hipótese inclui `relationId` e confidence, e nunca é gravada no perfil confirmado.

Snapshots e deltas usam o formato `{"periods":{"YYYY-MM":{"demand":{},"availability":{}}}}`. Cada cenário alternativo aplica recursivamente seus deltas sobre o snapshot compartilhado. A comparação `GET /scenarios/{id}/compare/{other_id}` retorna premissas e diferenças por período; quando um período com demanda não tem disponibilidade, o cenário é `incomplete` e nenhuma métrica é calculada.

O DDL usa `hours` como unidade de carga inicial e exige datas de horizonte/período no primeiro dia do mês. A aplicação deve validar as mesmas regras antes de gravar; as constraints e triggers fornecem uma segunda barreira no banco.

## Testes

```powershell
python -m pytest
```