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

Com SQL*Plus instalado, conecte-se ao serviço e execute:

```powershell
sqlplus ITB2CTRF@//host:1521/service_name @database/oracle/001_initial_schema.sql
```

O DDL usa `hours` como unidade de carga inicial e exige datas de horizonte/período no primeiro dia do mês. A aplicação deve validar as mesmas regras antes de gravar; as constraints e triggers fornecem uma segunda barreira no banco.

## Testes

```powershell
python -m pytest
```