# Manual de Teste do MVP Betsalel

Este roteiro percorre o fluxo local de cadastro até uma execução reproduzível do
otimizador. Use dados fictícios ou autorizados para teste. Os exemplos de IDs abaixo
são ilustrativos; use os IDs que a API devolver para os registros criados.

## 1. Preparar o ambiente

1. Confirme que as oito migrations Oracle foram executadas em ordem, de
   `001_initial_schema.sql` a `008_demand_title_epic.sql` (esta última adiciona as
   colunas `TITLE` e `EPIC_NAME` às demandas e precisa rodar antes de subir esta
   versão da API). Não as reexecute
   em uma base que já tenha os objetos.
2. Preencha o `.env` local com as credenciais do schema Betsalel (`ORACLE_*`), do
   schema Portal (`PORTAL_ORACLE_*`), LDAP e sessão. Os dois acessos Oracle são
   distintos. Não compartilhe o `.env`, senhas ou `VOSKILL_SESSION_SECRET`.
   No mínimo, confira `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`, `LDAP_URL`,
   `LDAP_DOMAIN`, `PORTAL_ORACLE_USER`, `PORTAL_ORACLE_PASSWORD`,
   `PORTAL_ORACLE_DSN` e `VOSKILL_SESSION_SECRET`.
3. O Portal usa `LDAP_DOMAIN` antes da matrícula. `LDAP_TIMEOUT` e
   `LDAP_CONNECT_TIMEOUT` são informados em milissegundos; o Betsalel converte para
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

1. Informe matrícula e senha corporativas no formulário **Entrar no Betsalel** (tela
   de login com a identidade visual Vivo, no mesmo padrão do Portal).
2. O login valida a senha via LDAP e verifica usuário ativo, perfil ativo/não expirado
   e permissão da tela `VOSKILL` no Oracle do Portal.
3. `PODE_VISUALIZAR=S` permite consultar. `PODE_EDITAR=S` permite cadastrar e alterar
   dados. Um perfil somente de leitura deve conseguir consultar, mas recebe `403`
   ao salvar.
4. A matrícula normalizada é usada como `actor_id` das operações. O cookie da sessão
   é assinado, `HttpOnly`, `SameSite=Lax` e temporário. Use **Sair** para encerrá-lo.

### Menu principal

Depois do login, a barra superior tem seis menus; cada um abre uma tela:

| Menu | O que contém |
| --- | --- |
| **Mapa do cenário** | Seletor de cenário, cobertura, estados por skill, skills do cenário e **Risco por limiar configurado**. |
| **Decisão operacional** | **Plano operacional da alternativa** (seção 6). |
| **Cálculo** | **Otimização do cenário**, **Explicação da alternativa** e **Cenários e alternativas**. |
| **Pessoas** | Cadastro de pessoas e as competências (skills) de cada uma. |
| **Skills** | Catálogo de skills: lista e cadastro. |
| **Projetos** | Três abas: **Projetos**, **Demandas** e **Cenários**. |

As telas já visitadas mantêm o que você preencheu ao trocar de menu. As referências
a seções nos passos abaixo dizem em qual menu cada uma está.

## 3. Cadastrar pessoas e skills

1. Abra o menu **Pessoas**. A lista de pessoas e skills carrega sozinha ao abrir a tela;
   se falhar, aparece o erro e o botão **Tentar carregar novamente**.
2. Se o catálogo estiver vazio, use **Nova pessoa** e **Cadastrar pessoa**; a pessoa
   aparece na lista na hora. As skills são cadastradas no menu **Skills**, em **Nova
   skill**; ao voltar ao menu **Pessoas**, a lista é atualizada sozinha. Para corrigir
   o nome ou a descrição de uma skill, use **Editar** na tabela do menu **Skills**, altere
   os campos e selecione **Salvar alterações** (o nome não pode repetir o de outra skill).
3. Se já houver registros, escolha a pessoa no seletor e use **Consultar competências**.
4. Em **Cadastrar competência**, escolha uma skill existente, nível de 1 a 5, informe
   evidência verificável e data da revisão. Se a pessoa já tiver essa skill, use
   **Editar** na tabela em vez de duplicá-la.
5. A correção de nível/evidência grava histórico em
   `VSK_PERSON_COMPETENCY_HISTORY`.

## 4. Criar projeto e demanda

1. No menu **Projetos**, aba **Projetos**, crie um projeto, por exemplo `Atlas`, com horizonte
   mensal começando no primeiro dia do mês. Exemplo: `2026-11` a `2027-10`. A lista de
   projetos cadastrados aparece sozinha ao abrir a aba. Para corrigir o nome ou o
   horizonte de um projeto existente, use **Editar** na linha da lista, altere os
   campos e selecione **Salvar alterações**. O horizonte não pode deixar demandas
   fora do período; ajuste ou exclua essas demandas antes de reduzi-lo.
2. A unidade do MVP é `hours`; ela não é configurável pela tela.
3. Escolha uma skill existente, nível exigido de 1 a 5, período dentro do horizonte
   e carga maior ou igual a zero. Opcionalmente informe o **Épico ou história** (o
   campo sugere os já usados no projeto) e o **Título da tarefa**. Selecione
   **Registrar demanda**.
4. Cada demanda é uma tarefa para o otimizador e é atribuída inteira a uma pessoa.
   Por isso quebre cada épico em tarefas por skill com carga menor ou igual à
   disponibilidade mensal de uma pessoa (por exemplo, até 200 h).
5. Confirme que a tarefa aparece na tabela, agrupada pelo épico, com título, skill,
   nível, período e carga. A linha do épico mostra a quantidade de tarefas e o total de
   horas. Erros de horizonte, carga ou permissão aparecem na própria seção.
6. Para corrigir, use **Editar** na linha, altere os campos e selecione **Salvar
   alterações** (ou **Cancelar edição**). **Excluir** pede confirmação. Cenários já
   salvos não mudam, pois guardam um snapshot; para refletir a alteração, edite o
   cenário (seção 5) ou crie um novo.

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

1. No menu **Projetos**, aba **Cenários** (seção **Disponibilidade e cenário**), projetos
   e pessoas carregam sozinhos ao abrir a aba.
2. Selecione `Atlas`. A tela mostra a tabela **Demandas do projeto** (skill com nome,
   nível exigido, mês e carga) e a lista de participantes ativos. Essas demandas são
   o que o cenário precisa cobrir; a disponibilidade informada é comparada a elas.
3. Em **Cenário**, deixe **Novo cenário** para criar um cenário-base.
4. Marque cada pessoa que poderá receber alocação. A disponibilidade é por pessoa e
   por mês, não por skill: informe as horas de cada mês que tem demanda. Para
   preencher todos os meses de uma vez, digite o valor em **Carga horária mensal** da
   pessoa e depois ajuste os meses que forem exceção. Por exemplo, `P-001` com 40
   horas em `2026-01`.
5. Dê um nome ao cenário e selecione **Salvar cenário-base**.
6. A tela confirma com o nome do cenário. Ele passa a aparecer nos seletores de
   cenário (mapa, otimização e comparação) e o mapa carrega o cenário criado.

### Editar um cenário existente

1. No menu **Projetos**, aba **Cenários**, selecione o projeto e escolha o cenário em
   **Cenário**. O formulário é preenchido com nome, pessoas e horas por mês.
2. Altere nome, pessoas ou horas e selecione **Salvar alterações**.
3. A edição grava um novo snapshot imutável e mantém o anterior para auditoria. O
   snapshot é refeito com as demandas e competências atuais do projeto, então meses
   novos exigem disponibilidade.
4. Um cenário que já tem alternativas geradas não pode ser editado
   (`SCENARIO_HAS_ALTERNATIVES`). Nesse caso escolha **Novo cenário** e salve com
   outro nome. Execuções feitas antes da edição passam a aparecer como cenário não
   identificado nas listas de execução.

Se uma skill não estiver confirmada para uma pessoa, o snapshot registra nível zero
para o cálculo da lacuna; relações de skills podem contribuir com inferências no
mapa, mas não transformam a hipótese em competência confirmada.

## 6. Executar a otimização

1. No menu **Cálculo**, em **Cenário a calcular**, na seção **Otimização do cenário**, escolha o cenário
   pelo nome (formato `Projeto · Cenário`). O mesmo cenário pode ser trocado no
   seletor do topo da página, que carrega o mapa de cobertura.
2. Escolha parâmetros. Para reproduzir o exemplo use seed 42, população 20 e
   12 gerações. Seed é a semente do sorteio, população é o número de candidatas por
   geração e gerações é o número de rodadas de evolução. Valores maiores, como 64 e
   40, exploram mais combinações.
3. Selecione **Executar otimização**. O sistema busca o snapshot associado ao cenário
   e envia seus perfis, competências, disponibilidades e demandas ao NSGA-II.
4. Confira o `RUN-...`, algoritmo/versão, snapshot, seed, população e gerações. As
   alternativas mostram lacuna de competência (horas ponderadas pelo déficit de nível)
   e pico de utilização (maior carga dividida pela disponibilidade; 1,0 é 100%)
   separadamente. Violações rejeitadas aparecem em texto.
   Logo abaixo, **Cálculos realizados neste cenário** lista as execuções salvas do
   cenário escolhido (data, resultado, alternativas viáveis e rejeitadas, seed,
   população, gerações e `RUN-...`), da mais recente para a mais antiga. Use
   **Ver detalhe** na linha para abrir abaixo da tabela todas as alternativas daquele
   cálculo (por exemplo, as 51 ou 60 alternativas), com lacuna, pico de utilização e
   restrições rejeitadas.
   Todas as tabelas do sistema mostram 10 linhas por página; quando há mais, use
   **Anterior** e **Próxima** abaixo da tabela.
5. Se não houver alternativa viável, aumente a disponibilidade, inclua mais pessoas ou
   reduza demandas e salve o cenário. Nenhuma alocação é aplicada automaticamente.
6. Para decidir, abra o menu **Decisão operacional** (**Plano operacional da alternativa**, que abre na execução mais
   recente; troque em **Execução**):
   - **Tarefas que ninguém do cenário consegue cumprir:** demandas cujo nível exigido
     ninguém no cenário tem, qualquer que seja a alternativa.
   - **Alternativa mais segura:** sugestão por uma ordem de desempate explícita
     (menor excesso de horas acima da disponibilidade, depois menos tarefas sem
     competência, depois menos tarefas abaixo do nível, depois menor lacuna
     ponderada). Não é uma nota agregada nem uma aprovação.
   - **Tabela de alternativas:** sobrecarga, horas excedentes, pico de utilização e
     tarefas sem competência ou abaixo do nível; use **Ver plano** para abrir uma.
   - **Quem faz cada tarefa**, **Carga por pessoa e mês** (quem está sobrecarregado) e
     **O que mudar para ficar executável**, com a ação sugerida para cada problema.
   Uma alternativa pode ser "viável" para o otimizador (cada tarefa cabe na
   disponibilidade de uma pessoa) e ainda assim sobrecarregar alguém ao somar as
   tarefas do mês; o plano mostra essa sobrecarga. Títulos e épicos aparecem para
   cenários criados ou editados depois da migration 008.
7. Para ver o detalhe técnico de uma alternativa, use **Explicação da alternativa**:
   escolha a **Execução** (listada como `Projeto · Cenário · data/hora`) e a
   **Alternativa**, e selecione **Consultar explicação**.
8. Para comparar, use **Cenários e alternativas**. Na aba **Alternativas**, escolha a
   **Execução** e duas alternativas dela. Na aba **Cenários**, escolha **Cenário base**
   e **Cenário para comparar**. Não há ranking agregado.
9. No menu **Mapa do cenário**, em **Risco por limiar configurado**, escolha a **Skill crítica** e o número mínimo
   de pessoas confirmadas, depois **Salvar limiar**. O valor fica gravado por projeto
   e skill em `VSK_CRITICAL_SKILL_THRESHOLDS`; o painel lista as skills abaixo do
   limiar com as pessoas e evidências.

Reutilizar a mesma seed, snapshot e parâmetros torna a execução reproduzível para a
mesma versão do algoritmo. O resultado e suas premissas ficam registrados para
auditoria. Cada usuário vê as próprias execuções; perfis de auditoria veem as de todos.

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
| `SCENARIO_ALREADY_EXISTS` | Já existe cenário com esse nome no projeto; use outro nome. |
| `SCENARIO_HAS_ALTERNATIVES` | O cenário já tem alternativas e não pode ser editado; salve como novo cenário. |
| `SCENARIO_NOT_FOUND` | O cenário não existe; escolha outro na lista ou crie um cenário-base. |

Para verificar a sessão sem enviar senha, abra `http://127.0.0.1:8000/auth/me`; sem
cookie válido, a resposta esperada é `401`. A documentação OpenAPI fica em
`http://127.0.0.1:8000/docs`.