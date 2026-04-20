# MoviSys Platform - Comercial Multi-Tenant

Sistema profissional com backend API comercial, painel administrativo, autenticação JWT, multi-empresa por CNPJ, auditoria, backup e fluxo completo `LOCAL -> DEV -> PROD`.

## Arquitetura

- `backend/`
  - `api/` rotas, middlewares e dependências
  - `services/` regras de negócio
  - `repositories/` acesso a dados
  - `models/` ORM SQLAlchemy
  - `schemas/` contratos e validações Pydantic
  - `migrations/` SQL versionado
  - `scripts/` migrate/seed
- `frontend/`
  - painel administrativo modular por componentes JS
- `infra/`
  - `nginx/` proxy reverso, HTTP/HTTPS
  - `scripts/` setup/deploy/update/backup/restore/monitoramento
  - `env/` exemplos de ambiente
- `.github/workflows/`
  - `ci.yml`
  - `deploy-dev.yml`
  - `deploy-prod.yml`

## Funcionalidades Implementadas

- Login com JWT (`access` + `refresh`)
- Logout e revogação de refresh token
- Multi-tenant por CNPJ com isolamento por empresa
- Gestão de empresas
- Gestão de usuários
- Dashboard administrativo
- Logs de requisição e auditoria de operações
- Backup automático + rotação + teste de restore
- Nginx como proxy (`/` frontend, `/api` backend)
- Docker DEV e PROD
- CI e deploy automático DEV/PROD

## Endpoints Principais

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET/POST/PUT /api/v1/empresas`
- `GET/POST/PUT /api/v1/usuarios`
- `GET /api/v1/dashboard/summary`
- `GET /health`
- `GET /api/health`

## Autenticação JWT

- Senha com hash `bcrypt`
- Token `access` com expiração curta
- Token `refresh` persistido com hash e revogação
- Rotas protegidas por middleware/deps
- Base pronta para permissões por `role`

## Multi-Empresa (CNPJ)

- Tabela `empresas` com `cnpj` único
- Tabela `user_accounts` vinculada a `empresa_id`
- Isolamento por tenant em rotas de dados
- `superadmin` pode atuar globalmente

## Banco de Dados

Tabelas principais:

- `empresas`
- `user_accounts`
- `refresh_tokens`
- `audit_logs`

Migrations e seeds:

```bash
python -m backend.scripts.migrate
python -m backend.scripts.seed
```

Seed inicial:

- `admin@movisys.local`
- `Admin@123456`

## Rodando Local (LOCAL)

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Aplicação local:

- Frontend: `http://localhost:8080`
- API: `http://localhost:8080/api`

## Ambiente DEV (VPS DEV)

Fluxo automático ao subir na branch `dev`:

- workflow: `.github/workflows/deploy-dev.yml`
- script de deploy: `infra/scripts/deploy-dev.sh`
- update: `infra/scripts/update.sh` com `TARGET_ENV=dev`

Secrets esperados:

- `DEV_VPS_HOST`
- `DEV_VPS_USER`
- `DEV_VPS_SSH_KEY`
- `DEV_VPS_PORT` (opcional)

## Ambiente PROD (VPS PROD)

Fluxo automático ao subir na branch `main`:

- workflow: `.github/workflows/deploy-prod.yml`
- script de deploy: `infra/scripts/deploy-prod.sh`

Secrets esperados:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT`
- `DOMAIN` e `LETSENCRYPT_EMAIL` (opcional para HTTPS automático)

## Backup, Restore e Logs

Scripts:

- `infra/scripts/backup-db.sh`
- `infra/scripts/restore-db.sh`
- `infra/scripts/backup-rotate.sh`
- `infra/scripts/test-restore.sh`
- `infra/scripts/monitor-health.sh`

Cron:

- `infra/scripts/install-backup-cron.sh`
- `infra/scripts/install-monitoring-cron.sh`
- `infra/scripts/install-https-cron.sh`

## Segurança

- Banco não exposto publicamente
- Backend não exposto diretamente (somente via Nginx `/api`)
- Segredos via variáveis de ambiente e GitHub Secrets
- Senhas com `bcrypt`
- JWT assinado
- SSH por chave (workflow PROD)

## CI/CD

- `ci.yml`: valida backend e frontend
- `deploy-dev.yml`: deploy automático branch `dev`
- `deploy-prod.yml`: deploy automático branch `main`

## Continuidade do Projeto

Registro de retomada da fase comercial/VPS:

- `docs/RETOMADA_COMERCIAL_VPS_2026-04-20.md`

Status registrado:

- PR #1 aberta em `codex-commercial-platform`
- branch `dev` publicada
- checks da PR passando
- deploy DEV executado com sucesso no GitHub Actions
- PROD preparado para disparar no merge em `main`, desde que os GitHub Secrets estejam configurados

## Observações Operacionais

- Respeite o fluxo obrigatório: `LOCAL -> DEV -> PROD`
- Não faça deploy direto em PROD sem passar por DEV
- Mantenha backups e testes de restore ativos para continuidade do negócio
