# Continuidade do Projeto Sync (Registro Completo)

Data do registro: 2026-04-16  
Projeto: `INTEGRADO_WEB_XD`

## Protocolo de atuação

Toda execução futura deve seguir o documento base:
- [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md)

Esse protocolo define:
- seleção do especialista correto
- formato obrigatório de resposta
- foco em segurança, escalabilidade e manutenção

## 1) Objetivo geral solicitado

Construir uma plataforma comercial de sincronização de dados multi-tenant com:
- Controle total de fluxo de dados por tenant
- Configuração de origem (FROM) e destino (TO) pela API/painel
- Pipeline modular ETL (extract, transform, load)
- Segurança, escalabilidade, retenção e observabilidade

## 2) Requisitos solicitados (resumo)

- Multi-tenant obrigatório com isolamento por `empresa_id`/`tenant_id`
- Sincronização incremental com `uuid` + `data_atualizacao`
- UPSERT no banco central
- Retenção de 14 meses (archive/delete)
- API key por empresa + validações
- Arquitetura modular (API/Service/Repository/Model)
- Agente local (MariaDB) -> API FastAPI -> PostgreSQL central
- Deploy em Docker
- Painel administrativo para configurações
- Dashboard mais dinâmico e gráfico menor de movimentação
- Controle de servidor pela API/painel

## 3) Ambiente e dados informados por você

- Banco local MariaDB:
  - Host: `127.0.0.1`
  - Porta: `3308`
  - Usuário: `root`
  - Senha: `root`
  - Database: `xd`
- Origem real usada: `salesdocumentsreportview`
- Banco central simulado no Docker: PostgreSQL

## 4) O que já foi implementado

## 4.1 Backend de sincronização (FastAPI)

Estrutura criada em `/backend` com camadas separadas:
- `api`, `services`, `repositories`, `models`, `schemas`, `config`, `utils`

Funcionalidades entregues:
- `POST /sync` com validação de tenant
- Autenticação por API key por tenant
- UPSERT por `uuid` com isolamento por `empresa_id`
- Métricas em `GET /metrics`
- Healthcheck em `GET /health`
- Job de retenção (14 meses)
- Endpoints admin:
  - `POST /admin/tenants`
  - `POST /admin/tenants/{empresa_id}/rotate-key`
  - `GET /admin/server-settings`
  - `PUT /admin/server-settings`

Configuração de servidor já controlável via API:
- `ingestion_enabled`
- `max_batch_size`
- `retention_mode` (`archive`/`delete`)
- `retention_months`

## 4.2 Agente local

Estrutura em `/agent_local`:
- leitura incremental do MariaDB
- checkpoint local
- envio em lote para API
- preflight de saúde (MariaDB/API)
- auditoria em arquivo (`/shared/agent_audit.log`)
- chave lida dinamicamente de arquivo (`/shared/agent_api_key.txt`)

## 4.3 Docker

Arquivo principal:
- `infra/docker/docker-compose.sync.yml`

Serviços:
- `postgres-central`
- `sync-api`
- `local-agent`

Ajuste aplicado:
- `sync-api` com `healthcheck`
- `local-agent` depende de `sync-api healthy`
- isso evita erro de startup `Connection refused` no preflight inicial

## 4.4 Painel admin (`sync-admin`)

Integração com a API de sync feita:
- provisionar tenant
- rotacionar API key
- atualizar key do agente automaticamente (`/shared/agent_api_key.txt`)
- visualizar status e métricas da API
- configurar servidor via formulário (server-settings)
- dashboard com atualização dinâmica
- exportação CSV de auditoria

Credenciais atuais do painel:
- URL: `http://localhost:8080/login`
- Usuário: `admin`
- Senha: `admin123`

## 5) Diagnóstico importante registrado

Mensagem vista:
- `mariadb_ok: true, api_ok: false, errors: ["api: [Errno 111] Connection refused"]`

Interpretação:
- Falha de conectividade no preflight (antes do `/sync`)
- Não era falha lógica da API de ingestão

Status após ajuste:
- `sync-api` saudável
- `local-agent` sincronizando com `POST /sync` retornando `200 OK`

## 6) Melhoria adicional concluída (métricas separadas)

Você pediu separar falhas para ficar claro:
- erro de conexão/preflight
- erro de aplicação no `/sync`

Implementado no painel:
- `sync_application_failures_total` (falha da aplicação de sync)
- `preflight_connection_errors_total` (erros de conexão/preflight do agente)

Arquivos alterados:
- `sync-admin/app/services/control_service.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/dashboard.html`
- `sync-admin/app/static/js/dashboard.js`
- `sync-admin/app/templates/settings.html`

## 7) Estado atual para retomada futura

Ponto atual:
- Plataforma funcional com sync real MariaDB -> API -> PostgreSQL docker
- Painel controla tenant, chave e server settings
- Dashboard dinâmico com KPIs separados de falha

Próximos passos recomendados para produção comercial:
1. Cadastro completo de múltiplas `sources` e `destinations` por tenant via API
2. Conectores plugin-like com descoberta automática no pacote (MariaDB, API externa, arquivo futuro)
3. Fila assíncrona robusta (Redis/RabbitMQ + worker dedicado)
4. Criptografia forte de credenciais em repouso (KMS/secret manager)
5. RBAC no painel admin e trilha de auditoria avançada
6. CI/CD + testes de carga + observabilidade (Prometheus/Grafana)

## 8) Pedido final registrado

Você solicitou também arquitetura comercial completa com:
- controle FROM/TO por tenant
- extensibilidade
- API-first

Esse desenho arquitetural já foi detalhado na conversa e deve ser a base da próxima fase de implementação.

## 9) Checklist consolidado (pedido x feito x faltando)

### 9.1 Checklist do que você pediu

- [x] API de sincronização multi-tenant
- [x] Agente local lendo MariaDB real
- [x] Sync incremental com UPSERT
- [x] Deploy em Docker
- [x] Dashboard/painel admin
- [x] Controle de servidor pela API/painel
- [x] Dashboard mais dinâmico
- [x] Gráfico de movimentação menor
- [x] Separar métrica de falha de conexão vs falha de aplicação
- [x] Registrar tudo para continuidade futura
- [x] Configuração completa FROM/TO por tenant (múltiplas origens/destinos plugáveis)
- [ ] Plataforma comercial full (RBAC avançado, conectores genéricos, fila enterprise, etc.)

### 9.2 Checklist do que foi feito (implementado)

- [x] Estrutura modular no backend (`api/services/repositories/models/schemas`)
- [x] Endpoint `POST /sync` com validação de tenant e API key
- [x] Endpoints admin de tenant e rotação de chave
- [x] Endpoints admin de `server-settings`
- [x] Métricas Prometheus (`/metrics`) e health (`/health`)
- [x] Retenção configurável (14 meses, archive/delete)
- [x] Agente com checkpoint incremental
- [x] Agente com preflight (MariaDB + API)
- [x] Auditoria de eventos/erros do agente em arquivo compartilhado
- [x] Docker compose do sync com `postgres-central`, `sync-api`, `local-agent`
- [x] Ajuste de startup via healthcheck + depends_on healthy
- [x] Painel integrado para provisionar tenant e rotacionar key
- [x] Escrita automática da key do agente pelo painel
- [x] Dashboard com atualização dinâmica (`/dashboard/data`)
- [x] Exportação CSV de auditoria
- [x] KPI separado:
  - [x] `sync_application_failures_total`
  - [x] `preflight_connection_errors_total`

### 9.3 Checklist do que falta (gap para comercial-ready completo)

- [x] API de cadastro de múltiplas `source_configs` por tenant (MariaDB/API/file)
- [x] API de cadastro de múltiplas `destination_configs` por tenant (Postgres/API externa)
- [x] Motor ETL com registry de conectores plugin-like completo e descoberta automática
- [ ] Scheduler por tenant orientado a configuração persistida (intervalo por fonte)
- [ ] Fila assíncrona robusta (Redis/RabbitMQ + worker pool + DLQ)
- [ ] Criptografia de credenciais com KMS/secret manager (além de env/file)
- [ ] RBAC (perfis/escopos) no painel/admin API
- [ ] Auditoria administrativa completa (quem alterou o quê e quando)
- [ ] Observabilidade completa (dashboards de latência, retries, throughput por tenant)
- [ ] Hardening de segurança (rate-limit, rotação de chaves administráveis, políticas)
- [ ] Testes de carga e plano de capacidade
- [ ] Pipeline CI/CD de produção com migrações e rollback

## 10) Nova solicitação registrada para continuidade

Você pediu uma nova fase de produto para uma API comercial multi-tenant com configuração dinâmica de origem e destino de dados. Este é o requisito que deve orientar a próxima execução.

### 10.1 Objetivo da nova fase

- Criar uma API modular, pronta para produção, com configuração de:
  - origem de dados
  - destino de dados
- Tornar essa configuração dinâmica, sem alteração de código para novos cenários suportados
- Preparar a solução para uso comercial e deploy futuro em cloud

### 10.2 Requisitos centrais

- Multi-tenant com identificação por CNPJ
- Isolamento estrito entre tenants
- Cada registro precisa carregar `tenant_id` ou `cnpj`
- Retenção de apenas 14 meses no banco central
- Extração, transformação e entrega de dados em fluxo automático
- Execução a cada 15 minutos, com intervalo configurável

### 10.3 Configuração de origem

- Tipos de origem previstos:
  - `mysql`
  - `mariadb`
  - `postgres`
- Campos principais:
  - host
  - port
  - database_name
  - username
  - password
  - extraction_interval

### 10.4 Configuração de destino

- Tipos de destino previstos:
  - banco de dados
  - API externa
- Campos principais:
  - api_url ou conexão de banco
  - host
  - port
  - database_name
  - username
  - password

## 11) Checkpoint de hotfix produção - 2026-04-27

### 11.1 Estado operacional

- Branch local: `codex/fix-connected-apis-nginx`.
- Produção VPS já corrigida manualmente:
  - Nginx recarregado com rotas para `/connected-apis`, `/reports` e `/client/reports`.
  - PostgreSQL recebeu `branch_code` e `terminal_code` em `vendas` e `vendas_historico`.
- Validação pública autenticada:
  - `/connected-apis` -> `200`
  - `/admin/connected-apis` -> `200`
  - `/reports` -> `200`
  - `/admin/reports` -> `200`
- Validação local:
  - `py -3 -m pytest -q` -> `26 passed, 1 skipped`

### 11.2 Estado Git

- Mudanças locais estão staged.
- Commit final ainda não foi criado porque a execução foi interrompida.
- Mensagem sugerida:
  - `fix: restore reports route and sales branch schema`
- Depois:
  - `git push -u origin codex/fix-connected-apis-nginx`
  - abrir PR para `main`
- `main` está protegida; não usar push direto.

### 11.3 Arquivos staged

- `backend/models/venda.py`
- `backend/repositories/venda_repository.py`
- `backend/schemas/sync.py`
- `backend/sql/postgresql_schema.sql`
- `infra/nginx/default.conf`
- `tests/test_production_operations.py`
- `tests/test_sync_upsert.py`
- `RETOMADA_EXATA.md`
- `cerebro_vivo/estado_atual.md`
- `REGISTRO_DE_MUDANCAS.md`
- `CONTINUIDADE_PROJETO_SYNC.md`

### 11.4 Proximo comando recomendado

```powershell
git add RETOMADA_EXATA.md cerebro_vivo/estado_atual.md REGISTRO_DE_MUDANCAS.md CONTINUIDADE_PROJETO_SYNC.md
git commit -m "fix: restore reports route and sales branch schema"
git push -u origin codex/fix-connected-apis-nginx
```

## 12) Checkpoint de convergencia backend/VPS - 2026-04-27

### 12.1 Diagnostico

- A VPS foi alinhada com `origin/main` para remover drift manual.
- O alinhamento confirmou um risco real: parte do backend avancado existia na VPS/branch antiga, mas nao estava no `main`.
- O downgrade quebrou `/reports` no painel porque o frontend chamava endpoints backend ausentes no `main`.
- Sintomas observados:
  - `/healthz`, `/readyz/backend` e `/admin/api/health/ready` estavam `200`.
  - `/connected-apis` estava `200`.
  - `/reports` autenticado retornava `500`.
  - logs do `sync-admin` indicavam `404` no backend para relatorios e resumo/listagem de clientes.

### 12.2 Correcao em andamento

- Branch local: `codex/restore-backend-reporting-contract`.
- Restaurado o contrato backend avancado a partir de `origin/codex/vps-https-deploy-contract`.
- Componentes restaurados:
  - rotas de relatorios por tenant;
  - rotas de clientes remotos/APIs conectadas;
  - rotas de pareamento por codigo;
  - schemas, services e repositories correlatos;
  - migrations e runner de banco;
  - readiness avancado;
  - auditoria com `correlation_id`;
  - metricas HTTP/fila/scheduler;
  - scheduler/worker avancados com retry e DLQ.
- Ajuste tecnico local:
  - `tenant_pairing_router` registrado no `backend/main.py` e em `backend/api/routes/__init__.py`;
  - politica de retry do worker ajustada para permitir tentativas antes de DLQ.

### 12.3 Validacao

- `py -3 -m pytest tests/test_production_operations.py tests/test_sync_upsert.py tests/test_api_integration.py -q`
  - Resultado: `13 passed`
- `py -3 -m pytest tests/test_tenant_scheduler.py -q`
  - Resultado: `3 passed`
- `py -3 -m pytest -q`
  - Resultado: `26 passed, 1 skipped`

### 12.4 Proximo passo operacional

```powershell
git add -A
git commit -m "fix: restore backend reporting and remote client contract"
git push -u origin codex/restore-backend-reporting-contract
```

- Abrir PR para `main`.
- Fazer merge aprovado.
- Deploy na VPS.
- Validar em producao:
  - `https://movisystecnologia.com.br/healthz`
  - `https://movisystecnologia.com.br/readyz/backend`
  - `https://movisystecnologia.com.br/admin/api/health/ready`
  - `https://movisystecnologia.com.br/admin/connected-apis`
  - `https://movisystecnologia.com.br/admin/reports`

## 13) Relatorios cliente/admin evoluidos - 2026-04-27

### 13.1 Decisao de produto

- Relatorios nao devem ser modulo operacional principal do admin.
- Cliente acessa relatorios em `/client/reports`.
- Admin mantem `/reports` apenas para teste tecnico e suporte.
- Menu principal do admin nao exibe mais `Relatorios`.

### 13.2 Entregue

- Filtros de relatorio:
  - vendas do dia;
  - mensal;
  - trimestral;
  - semestral;
  - anual;
  - datas X a Y;
  - horario X a Y;
  - filial;
  - terminal.
- Novos graficos:
  - serie diaria;
  - top produtos;
  - tipo de venda;
  - forma de pagamento;
  - familia do produto.
- Modelo canonico de venda expandido com campos opcionais:
  - `tipo_venda`;
  - `forma_pagamento`;
  - `familia_produto`.
- Novo endpoint backend:
  - `/admin/tenants/{empresa_id}/reports/breakdown`
- Nova migracao:
  - `v005_sales_report_dimensions`

### 13.3 Validacao

- Local:
  - `py -3 -m pytest -q`
  - Resultado: `27 passed, 1 skipped`
- VPS:
  - branch: `codex/restore-backend-reporting-contract`
  - commit: `fd8fb8b`
  - migracao: `current_version=5`
  - smoke:
    - `health=200`
    - `ready=200`
    - `login=302`
    - `reports=200`
    - `connected_apis=200`

### 13.4 Pendente

- Abrir PR da branch `codex/restore-backend-reporting-contract`.
- Fazer merge em `main`.
- So depois voltar a VPS para seguir `main`.

## 14) Portal cliente acessivel por admin - 2026-04-28

### 14.1 Decisao

- Admin pode acessar qualquer portal de cliente em modo suporte.
- Acesso deve ser sempre filtrado por `empresa_id`.
- O perfil `client` permanece limitado ao seu proprio tenant e escopo de filiais.
- Perfis nao autorizados continuam recebendo `403`.

### 14.2 Entregue

- Guard dedicado para portal cliente:
  - `require_client_portal_access`
- Rotas do portal cliente aceitando preview administrativo:
  - `/client/dashboard?empresa_id=<empresa_id>`
  - `/client/reports?empresa_id=<empresa_id>`
  - exportacoes CSV/XLSX/PDF com `empresa_id`.
- Templates exibem aviso quando o admin esta visualizando portal cliente.
- Teste automatizado cobre resolucao de escopo admin para qualquer `empresa_id`.

### 14.3 Validacao

- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### 14.4 Deploy

- Branch:
  - `codex/restore-backend-reporting-contract`
- Commit:
  - `c258d71` - `fix: allow admin client portal preview`
- VPS:
  - deploy executado;
  - containers saudaveis;
  - commit aplicado em `/opt/integrado_web_xd`.

### 14.5 Pendente

- GitHub CLI local esta desautenticado.
- Criar/atualizar PR da branch `codex/restore-backend-reporting-contract` para `main` apos reautenticacao.
- Nao fazer deploy de `main` antes de mergear essa branch.

## 15) Admin com acesso visivel ao portal cliente - 2026-04-28

### 15.1 Decisao

- Admin deve ter acesso a todas as telas, incluindo telas do portal cliente.
- Esse acesso nao pode remover isolamento do perfil `client`.
- A navegacao do admin deve mostrar o portal cliente diretamente, sem depender de URL manual.

### 15.2 Entregue

- Permissoes RBAC de portal cliente adicionadas ao perfil `admin`.
- Menu lateral do admin passou a exibir:
  - `Portal Cliente`
  - `Relatórios Cliente`
- Os links usam `CONTROL_EMPRESA_ID` como tenant padrao operacional.
- O guard `require_client_portal_access` continua aceitando:
  - `client` com `empresa_id`;
  - `admin`;
  - rejeitando demais perfis.

### 15.3 Validacao

- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### 15.4 Controle de PR

- Antes do push foi feito `git fetch origin`.
- `origin/main` foi incorporado na branch.
- Conflito em `tests/test_sync_admin_rbac.py` foi resolvido localmente.
- Suite completa passou depois do merge.
- Push executado para `codex/restore-backend-reporting-contract`.

## 16) Modernizacao BI do painel de relatorios - 2026-04-28

### 16.1 Direcao

- Modernizar a experiencia de relatorios para padrao comercial inspirado em Power BI, Metabase, Tableau e SaaS B2B.
- Nao reescrever para React neste ciclo para evitar alto risco de regressao.
- Preparar endpoints JSON modulares para futura migracao de frontend.

### 16.2 Entregue

- Layout BI responsivo:
  - KPIs no topo;
  - filtros globais;
  - graficos de linha, barra e donut;
  - comparativo com periodo anterior;
  - status da API local;
  - tabela detalhada;
  - tema claro/escuro;
  - busca e ordenacao local na tabela.
- KPIs obrigatorios implementados:
  - total faturado;
  - total de registros;
  - ticket medio;
  - crescimento percentual;
  - comparativo com periodo anterior;
  - ultima sincronizacao recebida;
  - status da API local conectada.
- Endpoints JSON:
  - `/reports/api/dashboard`
  - `/reports/api/kpis`
  - `/reports/api/charts`
  - `/reports/api/table`
  - `/reports/api/sync-status`
  - `/reports/api/export/pdf`
  - `/reports/api/export/excel`
  - `/reports/api/export/csv`
- Aliases locais mantidos:
  - `/api/reports/dashboard`
  - `/api/reports/kpis`
  - `/api/reports/charts`
  - `/api/reports/table`
  - `/api/reports/sync-status`
  - `/api/reports/export/pdf`
  - `/api/reports/export/excel`
  - `/api/reports/export/csv`
- Atualizacao automatica:
  - KPIs atualizados sem reload completo.
- Drill-down inicial:
  - clique em grafico filtra a tabela detalhada.
- Regra de 14 meses aplicada no resolver de periodo.

### 16.3 Segurança e multi-tenant

- `client` continua limitado ao proprio `empresa_id`.
- Admin/analyst usam permissao `reports.view`.
- Resolucao de empresa acontece antes de montar payload de relatorio.
- Nenhum endpoint novo consulta relatorio sem resolver o tenant do usuario.

### 16.4 Validacao

- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `29 passed, 1 skipped`

### 16.5 Proximo passo

- Fazer merge da branch em `main`.
- Deployar VPS a partir de `main`.
- Validar visual em `https://movisystecnologia.com.br/admin/client/reports?empresa_id=12345678000199`.

## 17) Hotfix PDF legivel de relatorios - 2026-04-28

### 17.1 Problema

- Exportacao PDF estava tecnicamente gerando arquivo, mas sem layout legivel.
- O conteudo saia comprimido, como texto corrido.

### 17.2 Entregue

- PDF de relatorio passou a ter estrutura:
  - titulo;
  - data de geracao;
  - filtros e resumo;
  - indicadores;
  - tabela de serie diaria;
  - tabela de top produtos;
  - tabela de vendas recentes.
- Renderizacao passou a ser paginada.
- Nenhuma dependencia externa foi adicionada.

### 17.3 Validacao

- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `4 passed`
- `py -3 -m pytest -q`
  - Resultado: `30 passed, 1 skipped`

## 18) Hotfix CSV/Excel simples para cliente - 2026-04-28

### 18.1 Problema

- CSV nao funcionava em alguns cenarios por campos extras no payload de vendas recentes.
- Excel estava dificil para cliente entender por usar nomes tecnicos em ingles.

### 18.2 Entregue

- CSV com colunas simples:
  - `Data`
  - `Produto`
  - `Valor`
  - `Pagamento`
  - `Tipo`
  - `Familia`
  - `Filial`
  - `Terminal`
  - `Codigo`
- CSV passou a usar `;` como separador.
- Excel simplificado com abas:
  - `Resumo`
  - `Vendas`
  - `Produtos`
  - `Dias`
- Campos extras do backend nao quebram mais CSV.

### 18.3 Validacao

- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `5 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

## 19) Hotfix 404 Portal Cliente - 2026-04-28

### 19.1 Problema

- Portal do cliente retornava `404 Not Found nginx/1.27.5`.
- O link `/client/dashboard` era gerado pelo painel, mas nao existia rota explicita no Nginx de producao.

### 19.2 Entregue

- Nginx passou a encaminhar `/client/dashboard` para o `sync-admin`.
- Rota `/client/reports` foi preservada.
- Admin continua autorizado a acessar todas as telas do cliente.
- Perfil `client` continua restrito ao proprio portal/empresa.

### 19.3 Validacao

- `py -3 -m pytest tests\test_production_operations.py -q`
  - Resultado: `8 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

### 19.4 Proximo passo operacional

- Commitar hotfix.
- Push da branch.
- Deploy na VPS.
- Validar `https://movisystecnologia.com.br/client/dashboard?empresa_id=12345678000199` sem 404 do Nginx.

## 20) Padronizacao AdminLTE global - 2026-04-28

### 20.1 Objetivo

- Tornar o AdminLTE o template visual oficial do `sync-admin`.
- Remover a sensacao de layout cru/formulario tecnico nas telas internas.
- Manter endpoints, permissoes e isolamento multiempresa fora da camada visual.

### 20.2 Entregue

- `base.html` virou shell AdminLTE global com sidebar, navbar, content wrapper, breadcrumb e footer.
- `login.html` passou a usar `login-page`, `login-box` e `card-outline`.
- Menu lateral recebeu entradas para dashboard, relatorios, empresas, usuarios, APIs conectadas, sincronizacoes, logs, configuracoes, backup e sair.
- Relatorios agora usam AdminLTE no dashboard BI:
  - `small-box` para KPIs;
  - `card card-outline` para graficos;
  - filtros compactos em card lateral;
  - tabela responsiva com busca, ordenacao e paginacao local.
- Criado partial de componentes reutilizaveis:
  - `sync-admin/app/templates/partials/adminlte_components.html`
- Filtro `Categoria` deixou de ser apenas visual e passou a filtrar no backend por produto/familia com `empresa_id`.

### 20.3 Validacao

- `py -3 -m compileall sync-admin/app backend`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py tests/test_sync_upsert.py tests/test_sync_admin_sync_cockpit.py -q`
  - Resultado: `14 passed`
- `py -3 -m pytest -q`
  - Resultado: `33 passed, 1 skipped`

### 20.4 Proximo passo operacional

- Commitar a padronizacao AdminLTE.
- Push da branch.
- Deploy VPS.
- Validar visual real no navegador:
  - `/login`
  - `/dashboard`
  - `/connected-apis`
  - `/client/dashboard`
  - `/client/reports`
  - `/settings`
