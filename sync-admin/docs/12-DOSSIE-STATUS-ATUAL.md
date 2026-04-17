# Dossiê de Status Atual

## Objetivo deste documento
Registrar exatamente onde o projeto parou, o que já foi entregue e o que ainda precisa evoluir.

## Data de referência
- Atualizado em: 2026-04-15

## Escopo entregue até agora

### Estrutura e arquitetura
- Projeto modular criado em `sync-admin/`.
- Separação por camadas implementada:
  - `api/routes`
  - `web/routes`
  - `models`
  - `repositories`
  - `services`
  - `config`
  - `core`
  - `templates`
  - `static`

### Backend/API
- Endpoint de saúde:
  - `GET /health`
- Endpoint principal de sincronização:
  - `POST /api/sync-data`
- Validações de payload com Pydantic.
- Autenticação da integração por `X-API-Key`.
- Registro de IP de origem, status e quantidade de registros por lote.

### Banco de dados
- Banco operacional: PostgreSQL via Docker (`sync_db`).
- Modelos principais implementados:
  - `users`
  - `integration_keys`
  - `sync_batches`
  - `sync_records`
- Bootstrap automático no startup:
  - usuário admin inicial
  - chave de integração inicial

### Painel web
- Login com sessão.
- Rotas administrativas:
  - `/dashboard`
  - `/records`
  - `/history`
  - `/settings`
- Painel com cards de resumo e gráfico com Chart.js.
- Lista de registros com filtro e paginação.
- Histórico de sincronizações.
- Exportação CSV de registros.

### Segurança
- Senha com hash (`bcrypt` + `passlib`).
- Sessão para rotas administrativas.
- Chave de integração armazenada com hash.
- Segredos via `.env`.

### Containers/deploy
- Stack em Docker Compose operacional:
  - `sync_db` (PostgreSQL)
  - `sync_api` (FastAPI)
  - `sync_web` (Nginx)
- Acesso validado por `http://localhost:8080`.

### Documentação
- Pacote completo em `sync-admin/docs`.
- Runbook, diagnóstico, roteiro e exemplos de integração já documentados.

## Estado operacional atual
- API responde em `GET /health`.
- Ingestão via `POST /api/sync-data` validada com resposta de sucesso.
- Painel web ativo em `/login`.

## Credenciais e chaves atuais (ambiente local)
- Usuário painel: `admin`
- Senha painel: `admin123`
- Chave de integração padrão: `sync-key-change-me`

## Pendências priorizadas (próxima fase)

### P1 (curto prazo)
- Exportação Excel e PDF.
- Controle de acesso por perfil no painel, além de admin único.
- Filtro avançado por empresa, filial e terminal em todas as telas.

### P2 (evolução)
- Multi-tenant completo com isolamento por empresa.
- Rotação e revogação de chaves de integração com interface administrativa.
- Endpoint de métricas para monitoramento (Prometheus).

### P3 (futuro)
- Integração com Obsidian/Nexus para trilha de auditoria e histórico.
- Escalabilidade horizontal da API + fila assíncrona para ingestão massiva.

## Definição de checkpoint
Se o projeto for pausado aqui, para retomar:
1. Subir containers com `docker compose --env-file .env up -d --build`.
2. Confirmar `GET /health`.
3. Validar login em `/login`.
4. Enviar lote de teste em `POST /api/sync-data`.
5. Verificar painel e histórico.
