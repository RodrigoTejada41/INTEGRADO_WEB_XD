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
2. Conectores plugin-like (MariaDB, API externa, arquivo futuro)
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
- [ ] Configuração completa FROM/TO por tenant (múltiplas origens/destinos plugáveis)
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

- [ ] API de cadastro de múltiplas `source_configs` por tenant (MariaDB/API/file)
- [ ] API de cadastro de múltiplas `destination_configs` por tenant (Postgres/API externa)
- [ ] Motor ETL com registry de conectores plugin-like completo
- [ ] Scheduler por tenant orientado a configuração persistida (intervalo por fonte)
- [ ] Fila assíncrona robusta (Redis/RabbitMQ + worker pool + DLQ)
- [ ] Criptografia de credenciais com KMS/secret manager (além de env/file)
- [ ] RBAC (perfis/escopos) no painel/admin API
- [ ] Auditoria administrativa completa (quem alterou o quê e quando)
- [ ] Observabilidade completa (dashboards de latência, retries, throughput por tenant)
- [ ] Hardening de segurança (rate-limit, rotação de chaves administráveis, políticas)
- [ ] Testes de carga e plano de capacidade
- [ ] Pipeline CI/CD de produção com migrações e rollback

## 10) Nova solicitacao registrada para continuidade

Voce pediu uma nova fase de produto para uma API comercial multi-tenant com configuracao dinamica de origem e destino de dados. Este e o requisito que deve orientar a proxima execucao.

### 10.1 Objetivo da nova fase

- Criar uma API modular, pronta para producao, com configuracao de:
  - origem de dados
  - destino de dados
- Tornar essa configuracao dinamica, sem alteracao de codigo para novos cenarios suportados
- Preparar a solucao para uso comercial e deploy futuro em cloud

### 10.2 Requisitos centrais

- Multi-tenant com identificacao por CNPJ
- Isolamento estrito entre tenants
- Cada registro precisa carregar `tenant_id` ou `cnpj`
- Retencao de apenas 14 meses no banco central
- Extracao, transformacao e entrega de dados em fluxo automatico
- Execucao a cada 15 minutos, com intervalo configuravel

### 10.3 Configuracao de origem

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

### 10.4 Configuracao de destino

- Tipos de destino previstos:
  - banco de dados
  - API externa
- Campos principais:
  - api_url ou conexao de banco
  - host
  - port
  - database_name
  - username
  - password

### 10.5 Regras de arquitetura

- Seguir clean architecture
- Separar:
  - config
  - database
  - services
  - api/controllers
  - jobs/workers
- Usar variaveis de ambiente e configuracao persistida em banco
- Manter estrutura modular e extensivel
- Evitar codigo monolitico

### 10.6 Regras de seguranca

- Criptografar dados sensiveis de configuracao
- Proteger endpoints com autenticacao por API Key ou JWT
- Impedir conflito entre tenants
- Evitar SQL injection e validacoes fracas

### 10.7 Observabilidade e operacao

- Registrar:
  - extracao
  - sync
  - erro
  - retry
- Incluir mecanismo de retry
- Incluir job de limpeza automatica para 14 meses

### 10.8 Testes obrigatorios

- Testes unitarios
- Testes de integracao
- Mock de conexoes de banco
- Validacao de isolamento multi-tenant
- Validacao de retention
- Validacao de upsert

### 10.9 Entregaveis esperados

- Codigo completo da API
- Modulo de configuracao
- Exemplo de arquivo de configuracao
- Schema de banco
- Worker/scheduler
- Documentacao de setup

### 10.10 Ordem sugerida de implementacao

1. Formalizar o modelo de configuracao de source e destination por tenant
2. Criar schemas, repositories e services para persistencia e validacao
3. Implementar registry de conectores
4. Amarrar scheduler por tenant
5. Fechar criptografia de credenciais
6. Consolidar retries, DLQ e retencao
7. Cobrir com testes unitarios e de integracao
8. Documentar setup e operacao

### 10.11 Status atual da nova fase

- [x] Item 1: modelo de configuracao de source e destination por tenant formalizado
- [x] Item 2: schemas, repositories e services ajustados para persistencia e validacao
- [x] Item 3: registry de conectores com validacao por direcao implementado
- [x] Item 4: worker com entrega para destinos configurados por tenant
- [x] Item 5: metricas e painel de destinacoes expostos para operacao
- [x] Item 6: endpoints de summary por tenant para source e destination expostos na API
- [x] Item 7: auditoria persistente de configuracoes por ator e acao
