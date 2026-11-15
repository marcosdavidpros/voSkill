# Manual de Teste do MVP voSkill

Este roteiro percorre o fluxo local de cadastro até uma execução reproduzível do
otimizador. Use dados fictícios ou autorizados para teste. Os exemplos de IDs abaixo
são ilustrativos; use os IDs que a API devolver para os registros criados.

## 1. Preparar o ambiente

1. Confirme que as sete migrations Oracle foram executadas em ordem, de
   `001_initial_schema.sql` a `007_critical_skill_thresholds.sql`. Não as reexecute
   em uma base que já tenha os objetos.
2. Preencha o `.env` local com as credenciais do schema voSkill (`ORACLE_*`), do
   schema Portal (`PORTAL_ORACLE_*`), LDAP e sessão. Os dois acessos Oracle são
   distintos. Não compartilhe o `.env`, senhas ou `VOSKILL_SESSION_SECRET`.
   No mínimo, confira `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`, `LDAP_URL`,
   `LDAP_DOMAIN`, `PORTAL_ORACLE_USER`, `PORTAL_ORACLE_PASSWORD`,
   `PORTAL_ORACLE_DSN` e `VOSKILL_SESSION_SECRET`.
3. O Portal usa `LDAP_DOMAIN` antes da matrícula. `LDAP_TIMEOUT` e
   `LDAP_CONNECT_TIMEOUT` são informados em milissegundos; o voSkill converte para
   segundos. `LDAP_FOLLOW_REFERRALS` aceita `true` ou `false`.
4. `LDAP_BASE_DN` é mantida por compatibilidade com o Portal, mas o login atual faz
   bind direto e não pesquisa por essa base.
5. Se `LDAP_URL=ldap://...`, as credenciais LDAP trafegam sem criptografia. Use
   somente na rede interna isolada aprovada pela empresa; prefira `ldaps://` quando
   disponível. Nesse caso, a validação do certificado é obrigatória. Configure
   `LDAP_CA_CERT` apenas se a CA corporativa não estiver na trust store do sistema.
6. Gere um `VOSKILL_SESSION_SECRET` próprio do ambiente, com pelo menos 32 bytes.
   A sessão padrão dura 1800 segundos. O cookie `Secure` permanece ativado por
   padrão; para HTTP local isolado, configure `VOSKILL_SESSION_COOKIE_SECURE=0`.

Inicie API e frontend em dois terminais PowerShell, na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m uvicorn voskill.main:app --env-file .env --host 127.0.0.1 --port 8000 --reload
npm run dev --prefix frontend
```

Abra o endereço local do Vite, normalmente `http://127.0.0.1:5173/`. Para
diagnóstico da API, `http://127.0.0.1:8000/health` deve responder `{"status":"ok"}`.

## 2. Entrar

1. Informe matrícula e senha corporativas no formulário **Entrar no voSkill**.
2. O login valida a senha via LDAP e verifica usuário ativo, perfil ativo/não expirado
   e permissão da tela `VOSKILL` no Oracle do Portal.
3. `PODE_VISUALIZAR=S` permite consultar. `PODE_EDITAR=S` permite cadastrar e alterar
   dados. Um perfil somente de leitura deve conseguir consultar, mas recebe `403`
   ao salvar.
4. A matrícula normalizada é usada como `actor_id` das operações. O cookie da sessão
   é assinado, `HttpOnly`, `SameSite=Lax` e temporário. Use **Sair** para encerrá-lo.

## 3. Cadastrar pessoas e skills

1. Na seção **Competências por pessoa**, selecione **Carregar pessoas e skills**.
2. Se o catálogo estiver vazio, use **Nova pessoa** e **Cadastrar pessoa**; depois
   cadastre uma skill em **Nova skill**. O formulário seleciona o registro recém-criado.
3. Se já houver registros, escolha a pessoa no seletor e use **Consultar competências**.
4. Em **Cadastrar competência**, escolha uma skill existente, nível de 1 a 5, informe
   evidência verificável e data da revisão. Se a pessoa já tiver essa skill, use
   **Editar** na tabela em vez de duplicá-la.
5. A correção de nível/evidência grava histórico em
   `VSK_PERSON_COMPETENCY_HISTORY`.

## 4. Criar projeto e demanda

1. Em **Projetos e demandas**, crie um projeto, por exemplo `Atlas`, com horizonte
   mensal começando no primeiro dia do mês. Exemplo: `2026-11` a `2027-10`.
2. A unidade do MVP é `hours`; ela não é configurável pela tela.
3. Escolha uma skill existente, nível exigido de 1 a 5, período dentro do horizonte
   e carga maior ou igual a zero. Selecione **Registrar demanda**.
4. Confirme que a linha aparece na tabela com ID `D-...`, skill, nível, período e
   carga. Erros de horizonte, carga ou permissão aparecem na própria seção.

Exemplo fictício de dados ponta a ponta. Os IDs abaixo são rótulos ilustrativos; na
aplicação use as opções e UUIDs devolvidos pelo cadastro:

| Registro | ID ilustrativo | Dados |
| --- | --- | --- |
| Pessoa | `P-001` | Alex |
| Skill | `SKILL-1` | Python |
| Competência | `C-001` | Python nível 4, evidência “Projeto Python”, revisão `2026-11-15` |
| Projeto | `PRJ-001` | Atlas, horizonte `2026-01` a `2026-12`, unidade hours |
| Demanda | `D-001` | Python nível 3, período `2026-01`, carga 10 hours |
| Cenário-base | `SCN-001` | P-001 disponível por 40 horas em `2026-01` |
| Snapshot | `SNP-001` | Base imutável usada no cálculo |
| Execução | `RUN-001` | Seed 42, população 20, 12 gerações |
| Alternativas | `A-001`, `A-002` | IDs ilustrativos de soluções da execução |

Exemplo fictício de demanda:

| Projeto | Skill | Nível | Período | Carga | Unidade |
| --- | --- | ---: | --- | ---: | --- |
| Atlas | Python | 3 | 2026-01 | 10 | hours |

## 5. Informar disponibilidade e montar cenário-base

1. Em **Disponibilidade e cenário**, escolha **Carregar projetos e pessoas**.
2. Selecione `Atlas`. A tela lista as demandas do projeto e os participantes ativos.
3. Marque cada pessoa que poderá receber alocação. Para cada pessoa selecionada,
   informe disponibilidade em horas para todos os meses que têm demanda. Por exemplo,
   `P-001` com 40 horas em `2026-01`.
4. Dê um nome ao cenário e selecione **Salvar cenário-base**.
5. A resposta mostra o ID do cenário `SCN-...` e do snapshot `SNP-...`. O mapa passa
   a carregar o cenário recém-criado.

Se uma skill não estiver confirmada para uma pessoa, o snapshot registra nível zero
para o cálculo da lacuna; relações de skills podem contribuir com inferências no
mapa, mas não transformam a hipótese em competência confirmada.

## 6. Executar a otimização

1. Confira que o cenário-base salvo está selecionado no mapa.
2. Na seção **Otimização do cenário**, escolha parâmetros. Para reproduzir o exemplo
   use seed 42, população 20 e 12 gerações.
3. Selecione **Executar otimização**. O sistema busca o snapshot associado ao cenário
   e envia seus perfis, competências, disponibilidades e demandas ao NSGA-II.
4. Confira o `RUN-...`, algoritmo/versão, snapshot, seed, população e gerações. As
   alternativas mostram lacuna de competência e pico de utilização separadamente;
   violações rejeitadas aparecem em texto.
5. Se não houver alternativa viável, ajuste dados de disponibilidade/demanda e crie
   outro cenário-base. Nenhuma alocação é aplicada automaticamente.
6. Para comparar alternativas, use a aba **Alternativas** da seção **Cenários e
   alternativas**, informe o ID da execução e dois IDs `A-...` que apareçam como
   viáveis no resultado. Não há ranking agregado.

Reutilizar a mesma seed, snapshot e parâmetros torna a execução reproduzível para a
mesma versão do algoritmo. O resultado e suas premissas ficam registrados para
auditoria.

## 7. IA e tokens

O cadastro, mapa, comparação e NSGA-II são determinísticos e **não precisam de token
de LLM**. O algoritmo evolutivo roda localmente usando `pymoo`; “gerações” e “população”
são parâmetros do otimizador, não chamadas de IA generativa.

Extração automática de competências e narrativa generativa não têm provider conectado
no código atual. Adicionar uma chave ao `.env` não ativa essas funções. Até existir uma
integração aprovada e configurada, esses pontos permanecem indisponíveis e o fluxo
determinístico continua utilizável.

## 8. Erros comuns

| HTTP/código | O que conferir |
| --- | --- |
| `401 AUTHENTICATION_REQUIRED` | Sessão ausente/expirada; entre novamente. |
| `401 INVALID_CREDENTIALS` | Matrícula/senha LDAP e liberação da matrícula no Portal. |
| `403 FORBIDDEN` | Usuário sem `VOSKILL PODE_VISUALIZAR` ou tentando escrever com perfil somente leitura. |
| `422 VALIDATION_ERROR` | Nível, mês, evidência, horizonte, unidade ou disponibilidade informados. |
| `503 AUTHENTICATION_UNAVAILABLE` | Configuração LDAP/Oracle Portal, rede ou serviço indisponível. |
| `PROJECT_HAS_NO_DEMANDS` | Cadastre pelo menos uma demanda antes do cenário-base. |
| `MISSING_AVAILABILITY` | Informe disponibilidade para cada participante em todos os meses com demanda. |
| `PERIOD_OUTSIDE_HORIZON` | Ajuste horizonte ou meses de demanda/disponibilidade. |

Para verificar a sessão sem enviar senha, abra `http://127.0.0.1:8000/auth/me`; sem
cookie válido, a resposta esperada é `401`. A documentação OpenAPI fica em
`http://127.0.0.1:8000/docs`.