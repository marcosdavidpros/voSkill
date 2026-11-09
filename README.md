# voSkill

## Desenvolvimento local

Requer Python 3.11 ou superior.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edite `.env` e preencha `ORACLE_USER`, `ORACLE_PASSWORD` e `ORACLE_DSN`. Use o formato Easy Connect para o DSN, por exemplo `//host:1521/service_name`. O arquivo `.env` é local e ignorado pelo Git; não coloque credenciais no `.env.example`.

Inicie a API com:

```powershell
python -m uvicorn voskill.main:app --reload
```

O endpoint `GET /health` não depende de conexão Oracle. A aplicação abre conexões somente quando uma operação de persistência solicitar.

## Oracle

O script `database/oracle/001_initial_schema.sql` cria as tabelas de pessoas, skills, competências/histórico, projetos e demandas, além de índices, constraints e triggers de horizonte. Todos os objetos usam o prefixo `VSK_` para identificar o projeto e evitar colisões. Os identificadores são UUIDs gerados pela aplicação. Execute o script uma vez conectado como owner `ITB2CTRF`; o guard interrompe a execução para qualquer outro usuário, e o script não remove nem recria tabelas existentes.

Com SQL*Plus instalado, conecte-se ao serviço e execute as migrations em ordem:

```powershell
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/001_initial_schema.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/002_scenarios.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/003_competency_suggestions.sql
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/004_suggestion_review.sql
```

`002_scenarios.sql` cria snapshots JSON imutáveis e cenários que compartilham o snapshot-base; overrides ficam separados em `DELTAS_JSON`. A migration aborta se os objetos já existirem, portanto não a reexecute após uma aplicação bem-sucedida.

`003_competency_suggestions.sql` cria a fila de revisão humana. A aplicação persiste somente o trecho exato de evidência e o SHA-256 da fonte, não o texto-fonte integral; sem extractor configurado, o endpoint retorna `PROVIDER_UNAVAILABLE`.

`004_suggestion_review.sql` adiciona os valores revisados e a referência opcional à competência confirmada. O endpoint `POST /people/{person_id}/competency-suggestions/{suggestion_id}/review` aceita `accept`, `edit` ou `reject`; somente requests autorizados pelo middleware atualizam o perfil, e a decisão e o histórico são gravados numa única transação.

Snapshots e deltas usam o formato `{"periods":{"YYYY-MM":{"demand":{},"availability":{}}}}`. Cada cenário alternativo aplica recursivamente seus deltas sobre o snapshot compartilhado. A comparação `GET /scenarios/{id}/compare/{other_id}` retorna premissas e diferenças por período; quando um período com demanda não tem disponibilidade, o cenário é `incomplete` e nenhuma métrica é calculada.

O DDL usa `hours` como unidade de carga inicial e exige datas de horizonte/período no primeiro dia do mês. A aplicação deve validar as mesmas regras antes de gravar; as constraints e triggers fornecem uma segunda barreira no banco.

## Testes

```powershell
python -m pytest
```