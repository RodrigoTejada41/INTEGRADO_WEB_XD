# Sync Admin Panel

Sistema web profissional, modular e escalável para recebimento de dados de sincronização, armazenamento e exibição administrativa.

## Documentacao completa

- Índice geral: [`docs/00-INDEX.md`](./docs/00-INDEX.md)
- Arquitetura: [`docs/01-ARQUITETURA.md`](./docs/01-ARQUITETURA.md)
- Banco de dados: [`docs/02-BANCO-DADOS.md`](./docs/02-BANCO-DADOS.md)
- API REST: [`docs/03-API.md`](./docs/03-API.md)
- Segurança: [`docs/04-SEGURANCA.md`](./docs/04-SEGURANCA.md)
- Painel web: [`docs/05-PAINEL-WEB.md`](./docs/05-PAINEL-WEB.md)
- Deploy Docker: [`docs/06-DEPLOY-DOCKER.md`](./docs/06-DEPLOY-DOCKER.md)
- Runbook operacional: [`docs/07-OPERACAO-RUNBOOK.md`](./docs/07-OPERACAO-RUNBOOK.md)
- Monitoramento e logs: [`docs/08-MONITORAMENTO-LOGS.md`](./docs/08-MONITORAMENTO-LOGS.md)
- Troubleshooting: [`docs/09-TROUBLESHOOTING.md`](./docs/09-TROUBLESHOOTING.md)
- Roadmap: [`docs/10-ROADMAP.md`](./docs/10-ROADMAP.md)
- Exemplos de integração: [`docs/11-EXEMPLOS-INTEGRACAO.md`](./docs/11-EXEMPLOS-INTEGRACAO.md)
- Dossiê de status atual: [`docs/12-DOSSIE-STATUS-ATUAL.md`](./docs/12-DOSSIE-STATUS-ATUAL.md)
- Fluxograma atual: [`docs/13-FLUXOGRAMA-ATUAL.md`](./docs/13-FLUXOGRAMA-ATUAL.md)
- Release checkpoint v0.1.0: [`docs/14-RELEASE-CHECKPOINT-v0.1.0.md`](./docs/14-RELEASE-CHECKPOINT-v0.1.0.md)
- Release registry: [`docs/15-RELEASE-REGISTRY.md`](./docs/15-RELEASE-REGISTRY.md)
- Changelog: [`REGISTRO_DE_MUDANCAS.md`](./REGISTRO_DE_MUDANCAS.md)
- Versao atual: [`VERSION`](./VERSION)

## Arquitetura modular

- `app/api/routes`: endpoints REST (`POST /api/sync-data`)
- `app/web/routes`: páginas do painel (login, dashboard, registros, histórico, configurações)
- `app/models`: entidades ORM (users, integration_keys, sync_batches, sync_records)
- `app/repositories`: acesso a dados desacoplado
- `app/services`: regras de negócio (auth, sync, dashboard, export)
- `app/config`: configuração por `.env`
- `app/core`: segurança, banco, logging
- `app/templates` e `app/static`: frontend administrativo responsivo

## Segurança

- Login com sessão para painel
- Senha com hash (`bcrypt`)
- API de integração protegida por `X-API-Key`
- Validação de payload com Pydantic
- Registro de IP de origem, data/hora e quantidade de registros

## Endpoint principal de integração

`POST /api/sync-data`

Headers:
- `X-API-Key: <chave>`

Body (exemplo):

```json
{
  "external_batch_id": "BATCH-20260415-001",
  "company_code": "ACME",
  "branch_code": "FILIAL-01",
  "terminal_code": "PDV-07",
  "sent_at": "2026-04-15T17:00:00Z",
  "records": [
    {
      "record_key": "DOC-1001",
      "record_type": "sale",
      "event_time": "2026-04-15T16:59:50Z",
      "payload": {"total": 120.90, "operator": "joao"}
    }
  ]
}
```

## Cenário com 2 containers (como solicitado)

- `sync_api`: backend + API + templates
- `sync_web`: frontend web (Nginx reverse proxy)
- Banco em serviço separado: `sync_db` (PostgreSQL)

## Subir ambiente

1. Copie `.env.example` para `.env`:
```powershell
Copy-Item .env.example .env
```

2. Suba os containers:
```powershell
docker compose up -d --build
```

3. Acesse:
- Painel web: `http://localhost:8080/login`
- Health API: `http://localhost:8080/health`

## Credenciais iniciais

- Usuário: `admin`
- Senha: `admin123`

## Diferenciais já preparados para evolução

- Campos de segmentação por `company_code`, `branch_code`, `terminal_code`
- Estrutura pronta para multiusuário e múltiplas unidades
- Exportação CSV implementada (`/records/export.csv`)
- Camadas desacopladas para troca de banco e expansão futura
- Base pronta para integração futura com Obsidian/Nexus para trilhas de auditoria

