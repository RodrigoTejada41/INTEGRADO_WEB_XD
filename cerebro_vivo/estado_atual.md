# Estado Atual

## Resumo executivo

O projeto e uma plataforma de sincronizacao de dados multi-tenant com memoria local-first em `.cerebro-vivo/` e uma camada executiva visivel em `cerebro_vivo/` para coordenacao multi-agentes.

Checkpoint mais recente em 2026-04-27: producao foi corrigida para as telas `APIs Conectadas` e `Relatorios`. O problema inicial era roteamento Nginx ausente para caminhos absolutos do `sync-admin`. Em seguida foi identificado erro backend por schema antigo de `vendas` sem `branch_code` e `terminal_code`. A VPS ja recebeu a correcao operacional e as mudancas locais estao staged na branch `codex/fix-connected-apis-nginx`, mas ainda sem commit final porque a sessao foi interrompida.

Na governanca oficial atual, `backend/`, `agent_local/`, `sync-admin/` e `infra/` sao as fontes canonicas operacionais. `backend/src`, `frontend`, `database`, `devops` e `docker-compose.yml` na raiz permanecem como camadas de compatibilidade e onboarding.

Na retomada canonica mais recente, o backlog funcional estava concluido ate `P18`. Considerando o estado corrente desta sessao, `P19` foi concluido com governanca conservadora de segredos e auditoria expandida nas rotas administrativas do backend, `P20` foi concluido com endurecimento operacional do deploy de producao, o backlog pos-`P20` ja teve a regra critica de retencao de 14 meses convertida em evidencia automatizada, e agora existe uma trilha funcional inicial de controle bidirecional entre `sync-admin` e `receiver-api`, acompanhada da nova camada de escopo de acesso do portal cliente.

## Base canonica consultada

- `RETOMADA_EXATA.md`
- `.cerebro-vivo/Logs/memory_standard.json`
- `.cerebro-vivo/Logs/processo_projeto.json`
- `.cerebro-vivo/00_PAINEL/PROCESSO_PROJETO.md`

## Estado consolidado encontrado

- Branch local atual: `codex/fix-connected-apis-nginx`
- Estado Git ao pausar: arquivos staged, sem commit final da ultima correcao de relatorios/schema
- Producao atual: Nginx recarregado e PostgreSQL migrado manualmente com `ADD COLUMN IF NOT EXISTS`
- Validacao mais recente: `py -3 -m pytest -q` com `26 passed, 1 skipped`
- Checkpoint canonico de retomada: backlog concluido ate P18
- Estado corrente desta sessao: P20 concluido + backlog pos-P20 em execucao
- Ultima entrega funcional consolidada: registro de instancias locais, fila de comandos remotos pull, endpoints protegidos de configuracao/status no `sync-admin`, controle central no `receiver-api` e portal cliente com escopo formal por empresa ou conjunto de filiais
- Ultima validacao registrada nesta camada executiva: `py -3 -m pytest tests/test_sync_admin_connected_apis.py tests/test_sync_admin_client_portal.py tests/test_sync_admin_reports.py tests/test_sync_admin_client_scope.py tests/test_sync_admin_settings_client_scope.py -q` com 10 testes aprovados
- Etapa adicional ja concluida no codigo: estrutura completa para deploy em VPS Linux com Docker, Nginx e GitHub Actions

## Entregas recentes registradas

1. P15 concluido: migracoes versionadas com rollback por versao/passos
2. P16 concluido: health/live/ready no backend e sync-admin
3. P17 concluido: backpressure por tenant e retry por classe de falha
4. P18 concluido: observabilidade por tenant no backend e no painel + correlacao de logs
5. P19 concluido nesta sessao: governanca e seguranca, com foco em rotacao/expiracao de segredos, mascaramento de configuracoes sensiveis e auditoria expandida de operacoes administrativas
6. P20 concluido nesta sessao: endurecimento operacional com workflow de producao mais tolerante, readiness reforcado no ambiente produtivo e testes de operacao para evitar regressao
7. Backlog pos-P20 avancado: cobertura dedicada para retencao de 14 meses nos modos `archive` e `delete`, incluindo preservacao do limite exato e de `empresa_id`
8. Fluxo bidirecional iniciado: `receiver-api` agora registra clientes locais, enfileira comandos remotos e acompanha snapshots de configuracao/status; `sync-admin` expoe `/api/v1/config`, `/api/v1/status`, `/api/v1/sync/force` e processa comandos por polling seguro
9. Observabilidade fim a fim fortalecida no fluxo remoto: `sync-admin` agora emite `X-Request-Id` e `X-Correlation-Id`, propaga correlacao nas chamadas ao `backend` e o `receiver-api` expoe esse rastro nos logs de clientes locais
10. Painel web centralizado de APIs conectadas entregue: a web agora lista todas as instancias registradas, permite filtrar por empresa/status/busca, abrir detalhe por cliente, ver logs remotos e enfileirar `force_sync` ou `update_config` pela interface
11. Configuracao segura de conexoes ampliada: source/destination configs agora podem apontar para `settings_file` ou `settings_env` com `settings_key`, permitindo resolver host, URL e credenciais no runtime sem expor esses dados no payload administrativo
12. Painel admin ganhou fluxo de servidores de conexao seguros: a web agora cadastra source/destination com referencia segura, usa arquivo de segredos configuravel no backend e pode gerar chave de acesso por servidor no momento da criacao
13. Rotacao de chave por servidor adicionada ao fluxo seguro: a mesma `settings_key` agora pode ter a credencial renovada pela web sem recriar a configuracao do tenant
14. Edicao do JSON secreto por servidor adicionada ao fluxo seguro: a web agora atualiza os campos secretos pela mesma `settings_key`, preservando a referencia e evitando recriacao de source/destination config
15. Frente web de relatorios iniciada no `sync-admin`: nova pagina `/reports` consome overview, serie diaria, top produtos e vendas recentes do backend admin, com filtros por periodo/filial/terminal e permissao dedicada para `admin` e `analyst`
16. Separacao formal entre portal admin e portal cliente: usuarios `client` agora exigem `empresa_id`, fazem login em uma trilha propria (`/client/dashboard` e `/client/reports`) e ficam restritos aos relatorios da propria empresa
17. Frente de relatorios amadurecida: portais admin e cliente agora exibem comparativo com o periodo anterior e expoem exportacao de relatorios em `CSV`, `XLSX` e `PDF`, mantendo o cliente preso ao `empresa_id` da propria sessao
18. Dashboard de relatorios consolidado: admin e cliente passaram a compartilhar um parcial visual unico, com metricas derivadas no servidor web e comparativo percentual contra o periodo anterior
19. Controle de escopo por cliente iniciado no `sync-admin`: usuarios `client` agora podem ser `company` ou `branch_set`, com `scope_type` em `users` e tabela dedicada `user_branch_permissions`
20. Portal cliente endurecido: o `sync-admin` agora resolve filiais permitidas por usuario, aceita matriz como `0001`, bloqueia filial fora do escopo e preenche filtros apenas com filiais autorizadas
21. Painel admin alinhado ao fluxo comercial aprovado: `/reports` agora aceita `empresa_id` para abrir relatorios de qualquer empresa no contexto administrativo, e a tela de APIs conectadas passou a exibir CNPJ, nome da empresa e atalho direto para relatorios
22. Backend central enriquecido para operacao: respostas de clientes remotos agora incluem `empresa_nome`, permitindo identificar melhor a frota de APIs conectadas na web administrativa
23. Gestao de acessos no painel admin ampliada: usuarios existentes agora podem ser editados no `sync-admin`, incluindo `full_name`, `role`, `empresa_id`, `scope_type`, filiais permitidas, status ativo e senha opcional
24. Auditoria local de identidade adicionada ao `sync-admin`: alteracoes de usuarios e de escopo agora geram eventos proprios em tabela local, separados da auditoria central de tenant/configuracoes
25. Legibilidade da auditoria local melhorada: a tela `settings` do `sync-admin` agora resume alteracoes de usuario por campo (`antes -> depois`) para empresa, escopo, filiais, perfil, nome e status, com fallback para JSON bruto apenas quando necessario
26. Auditoria local com severidade visual: a tela `settings` agora classifica eventos de acesso como `critico`, `atencao` ou `informativo` e destaca sinais como troca de empresa, troca de perfil, desativacao de usuario, mudanca de escopo e reducao de filiais autorizadas
27. Hotfix operacional de producao: Nginx passou a rotear `/connected-apis`, `/reports` e `/client/reports` para o `sync-admin`, eliminando 404 nas telas administrativas.
28. Schema de vendas alinhado aos relatorios: `vendas` e `vendas_historico` passaram a incluir `branch_code` e `terminal_code`, com persistencia no upsert e indices para filtros por filial/terminal.

## Proximos passos mapeados

1. Criar commit com as mudancas staged: `fix: restore reports route and sales branch schema`
2. Fazer push da branch `codex/fix-connected-apis-nginx`
3. Abrir/atualizar PR para `main`, porque `main` esta protegida
4. Depois do merge, confirmar que a VPS continua em estado convergente com o repositorio
5. Priorizar backlog pos-P20 com foco em risco operacional, seguranca e continuidade do produto
6. Revisar apenas itens residuais fora do escopo conservador de P20, se ainda houver necessidade operacional
7. Consolidar melhorias de UX e governanca no painel admin, incluindo refinamento visual da edicao de usuarios e eventual ampliacao visual da auditoria local de acessos

## Atualizacao desta continuidade

- Em 2026-04-27, foram corrigidas em producao as rotas `APIs Conectadas` e `Relatorios` no Nginx.
- O 404 de `/connected-apis` foi resolvido com rota compativel para o `sync-admin`.
- O 404 de `/reports` e `/client/reports` foi resolvido com rotas compativeis adicionais.
- O 500 da tela de relatorios foi rastreado ate o backend central, causado por ausencia de `branch_code` e `terminal_code` na tabela `vendas`.
- A VPS recebeu migracao SQL idempotente para `vendas` e `vendas_historico`, incluindo indices por `empresa_id + branch_code` e `empresa_id + terminal_code`.
- Validacao autenticada em producao confirmou `200` para `/connected-apis`, `/admin/connected-apis`, `/reports` e `/admin/reports`.
- O codigo local foi atualizado para refletir a producao: modelo ORM, payload de sync, upsert, schema SQL e testes.
- As mudancas estao staged na branch `codex/fix-connected-apis-nginx`; falta apenas commit, push e PR.
- A frente de relatorios do `sync-admin` passou a usar um dashboard visual compartilhado entre admin e cliente.
- As metricas executivas derivadas (`ticket medio`, `media diaria`, `melhor dia`, `produto lider`) agora sao calculadas no servidor web, reduzindo logica espalhada em template.
- O comparativo com o periodo anterior agora exibe tambem a variacao percentual.
- A modelagem aprovada para acesso cliente por empresa ou filiais especificas comecou a ser implementada no `sync-admin`, com `scope_type` em usuarios e tabela `user_branch_permissions`.
- O portal cliente agora resolve escopo pelo backend do `sync-admin`, lista apenas filiais permitidas e rejeita consultas fora desse escopo antes de chamar o backend central.
- O painel admin passou a abrir relatorios de uma empresa especifica via `empresa_id`, e a listagem de APIs conectadas agora identifica clientes por CNPJ e nome da empresa.
- O backend central passou a enriquecer a frota de clientes remotos com `empresa_nome` para apoiar o fluxo administrativo.
- Validacao direcionada apos essa etapa: `py -3 -m pytest tests/test_sync_admin_connected_apis.py tests/test_sync_admin_client_portal.py tests/test_sync_admin_reports.py tests/test_sync_admin_client_scope.py tests/test_sync_admin_settings_client_scope.py -q` com `10 passed`.
- O painel admin agora tambem edita usuarios existentes sem recriacao, incluindo mudanca de escopo `company` ou `branch_set`, substituicao de filiais permitidas, ativacao/inativacao e troca opcional de senha.
- Validacao direcionada da edicao administrativa: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py -q` com `3 passed`, seguida de regressao nas trilhas de portal cliente, relatorios e APIs conectadas com `8 passed`.
- O `sync-admin` agora registra auditoria local de identidade para `user.create`, `user.update` e `user.scope.update`, incluindo ator, alvo, correlacao, origem HTTP e snapshot before/after.
- A tela `settings` passou a expor uma secao dedicada de "Auditoria local de acessos", separada da auditoria central de configuracoes do backend.
- Validacao direcionada da nova trilha: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py -q` com `3 passed`, seguida de regressao curta em portal cliente, relatorios e APIs conectadas com `8 passed`.
- A auditoria local do `sync-admin` agora exibe resumo legivel por campo, destacando `antes -> depois` para empresa, escopo, filiais, perfil, nome e status, em vez de depender do dump bruto de dicionario.
- Validacao direcionada apos o refinamento visual: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py -q` com `3 passed`, seguida de regressao curta em portal cliente, relatorios e APIs conectadas com `8 passed`.
- A auditoria local do `sync-admin` agora tambem expõe severidade visual por evento e chips de sinalizacao para mudancas mais sensiveis, como alteracao de empresa, reducao de filiais e desativacao de usuario.
- Validacao operacional local do stack produtivo executada nesta maquina: migracao `scripts/db_migrate.py` aplicada antes da subida completa, containers `db`, `backend`, `frontend` e `nginx` saudaveis, e edge validado em `http://127.0.0.1:8088` porque a porta `80` do host estava ocupada.

## Registro operacional desta sessao

- `docker-compose.prod.yml` recebeu porta publica parametrizada via `NGINX_PUBLIC_PORT`; o valor local ficou em `8088` para evitar conflito com o host, mantendo `80` como default de producao.
- `.env.prod` local foi criado e mantido fora do Git para destravar o compose e permitir a validacao deste workspace sem expor segredos.
- O fluxo padrao ficou registrado como: alteracao local -> testes -> documentacao -> deploy na VPS de `dev` -> validacao -> promocao para producao.
- Foi criada a trilha de deploy `dev` separada em `.github/workflows/deploy-dev.yml`, com secrets dedicados para evitar misturar ambiente de desenvolvimento com producao.

## Backlog pos-P20

1. Fechar a trilha de seguranca operacional de producao
   - Motivo: reduzir risco real em ambiente produtivo para secrets, acesso admin e endurecimento de borda
   - Status: pendente
2. Validar explicitamente a retencao de 14 meses com teste dedicado
   - Motivo: transformar a regra critica de retencao em evidencia automatizada e verificavel
   - Status: concluido
3. Fortalecer observabilidade fim a fim por tenant
   - Motivo: facilitar troubleshooting real com correlation_id, logs por tenant e contexto operacional completo
   - Status: concluido
4. Revisar readiness e health de toda a cadeia produtiva
   - Motivo: garantir validacao fiel entre nginx, backend, sync-admin, banco e dependencias
   - Status: pendente
5. Consolidar runbooks operacionais recorrentes
   - Motivo: reduzir erro humano em deploy, rotacao de chaves, renovacao HTTPS e recuperacao pos-falha
   - Status: pendente
6. Revisar guardrails residuais de multi-tenant
   - Motivo: ampliar cobertura de empresa_id, autenticacao por tenant, uuid e upserts criticos
   - Status: pendente
7. Abrir o proximo marco oficial do backlog pos-P20
   - Motivo: transformar a lista pendente em trilha executavel com prioridade formal
   - Status: pendente
8. Endurecer a operacao bidirecional em producao
   - Motivo: complementar a entrega inicial com HTTPS obrigatorio de borda, rotacao operacional de tokens locais, IP allowlist real e sync de dados de negocio ponta a ponta
   - Status: pendente
9. Ampliar o painel central para a frota inteira de APIs conectadas
   - Motivo: transformar o `sync-admin` em console SaaS real para descoberta e administracao remota multi-tenant
   - Status: concluido

## Leituras obrigatorias para retomada

1. `AGENTS.md`
2. `PROTOCOLO_ESPECIALISTAS.md`
3. `.cerebro-vivo/README.md`
4. `cerebro_vivo/historico_decisoes.md`
5. `.cerebro-vivo/00_PAINEL/PROCESSO_PROJETO.md`

## Regra de convivencia entre as memorias

- `.cerebro-vivo/` continua como base detalhada e historica
- `cerebro_vivo/` resume contexto, decisoes e estado executivo
- Em caso de divergencia, prevalece a fonte canonica mais detalhada da `.cerebro-vivo/`, salvo atualizacao explicita em `AGENTS.md`

## Checklist rapido antes de agir

- Confirmar o papel do agente lider e os especialistas de apoio
- Validar impacto em multi-tenant com `empresa_id`
- Verificar autenticacao, retencao maxima de 14 meses e modularidade
- Tratar `RETOMADA_EXATA.md` como referencia principal para checkpoint e validacao mais recente
- Registrar qualquer nova decisao duradoura nesta camada executiva e na base operacional correspondente

## Estado desta pausa

- Checkpoint consolidado e pronto para retomada posterior.
- Referencia principal para reinicio: `RETOMADA_EXATA.md`.
- Referencia executiva para contexto resumido: este arquivo.
- A sessao foi pausada apos solicitar registro integral do estado para continuidade posterior.

## Atualizacao executiva - 2026-04-27

- Foi identificado downgrade funcional ao alinhar VPS com `origin/main`: producao possuia backend avancado fora do contrato versionado em `main`.
- A correcao foi isolada na branch `codex/restore-backend-reporting-contract`.
- O backend avancado foi restaurado para cobrir relatorios por tenant, APIs conectadas, pareamento por codigo, readiness, auditoria correlacionada, metricas e scheduler/worker com retry/DLQ.
- Validacao local completa: `py -3 -m pytest -q` com `26 passed, 1 skipped`.
- Proximo movimento seguro: commit, push, PR para `main`, merge aprovado e deploy na VPS com validacao autenticada de `/admin/reports` e `/admin/connected-apis`.

## Atualizacao de produto - relatorios - 2026-04-27

- Relatorios foram reposicionados:
  - cliente: uso principal em `/client/reports`;
  - admin: acesso a `/reports` apenas para teste tecnico/diagnostico.
- A navegacao principal do admin nao deve tratar relatorios como modulo operacional.
- O modelo canonico de venda passou a aceitar dimensoes opcionais para analise comercial:
  - tipo de venda;
  - forma de pagamento;
  - familia do produto.
- Filtros novos:
  - vendas do dia;
  - mensal, trimestral, semestral e anual;
  - intervalo de datas X a Y;
  - intervalo de horario X a Y baseado em `data_atualizacao`.
- Validacao local completa: `py -3 -m pytest -q` com `27 passed, 1 skipped`.
- Deploy final na VPS:
  - branch: `codex/restore-backend-reporting-contract`;
  - commit: `fd8fb8b`;
  - migracao: `current_version=5`;
  - smoke autenticado: `health=200`, `ready=200`, `login=302`, `reports=200`, `connected_apis=200`.
- Pendente obrigatorio:
  - mergear essa branch em `main` antes de qualquer deploy automatico de `main`.

## Atualizacao operacional - portal cliente por admin - 2026-04-28

- Admin pode acessar o portal cliente em modo suporte por `empresa_id`.
- Rotas principais:
  - `https://movisystecnologia.com.br/admin/client/dashboard?empresa_id=12345678000199`
  - `https://movisystecnologia.com.br/admin/client/reports?empresa_id=12345678000199`
- A regra de seguranca foi preservada:
  - `client` continua limitado ao proprio tenant;
  - `admin` precisa operar com `empresa_id` resolvido;
  - demais perfis continuam sem acesso ao portal cliente.
- Commit aplicado e publicado:
  - `c258d71` - `fix: allow admin client portal preview`
- Validacao local:
  - `py -3 -m pytest -q` com `28 passed, 1 skipped`.
- Deploy VPS:
  - branch `codex/restore-backend-reporting-contract`;
  - containers saudaveis apos `deploy-prod.sh`.
- Pendente:
  - GitHub CLI esta sem autenticacao local;
  - abrir/atualizar PR e mergear em `main` antes de qualquer deploy automatico de `main`.

## Atualizacao operacional - navegacao admin completa - 2026-04-28

- Admin deve acessar todas as telas, incluindo as telas do portal cliente.
- Menu lateral do admin agora inclui:
  - `Portal Cliente`
  - `Relatórios Cliente`
- O acesso usa o tenant padrao `CONTROL_EMPRESA_ID`, sem remover a opcao de trocar `empresa_id` pela URL.
- Perfil `client` continua isolado ao proprio `empresa_id`.
- Antes do push, a branch foi sincronizada com `origin/main` e conflito local foi resolvido.
- Validacao completa:
  - `py -3 -m pytest -q` com `28 passed, 1 skipped`.

## Atualizacao de produto - dashboard BI de relatorios - 2026-04-28

- Painel de relatorios modernizado para padrao SaaS/BI:
  - KPIs no topo;
  - filtros globais;
  - graficos de linha, barra e donut;
  - comparativo com periodo anterior;
  - status da API local;
  - tabela detalhada com busca e ordenacao;
  - tema claro/escuro;
  - responsividade desktop/tablet/celular.
- Endpoints JSON adicionados:
  - `/api/reports/dashboard`
  - `/api/reports/kpis`
  - `/api/reports/charts`
  - `/api/reports/table`
  - `/api/reports/sync-status`
  - `/api/reports/export/pdf`
  - `/api/reports/export/excel`
  - `/api/reports/export/csv`
- Regra de 14 meses agora e aplicada diretamente no resolver de periodo.
- Validacao completa:
  - `py -3 -m pytest -q` com `29 passed, 1 skipped`.
- Proximo passo operacional:
  - mergear branch em `main`;
  - deployar VPS a partir de `main`;
  - validar visual real no dominio.
