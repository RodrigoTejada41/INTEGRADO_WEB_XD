# Arquitetura

## Objetivo
Receber dados periodicos de sincronizacao via API, persistir em banco e disponibilizar consulta em painel web administrativo.

## Componentes
- `sync_web` (Nginx): entrada HTTP publica (`:8080`) e proxy reverso para API.
- `sync_api` (FastAPI): backend, API REST e paginas web (Jinja2).
- `sync_db` (PostgreSQL): persistencia principal.

## Modulos internos
- `app/api/routes`: rotas REST (`/health`, `/api/sync-data`).
- `app/web/routes`: rotas de interface (login, dashboard, registros, historico, configuracoes).
- `app/models`: entidades ORM.
- `app/repositories`: acesso a dados por repositorio.
- `app/services`: regras de negocio.
- `app/core`: seguranca, banco, logging.
- `app/config`: configuracoes por ambiente.

## Fluxo de dados
1. Sistema local envia `POST /api/sync-data` com `X-API-Key`.
2. Backend valida autenticacao e payload (Pydantic).
3. Backend grava lote em `sync_batches` e registros em `sync_records`.
4. Painel consulta dados agregados e historico.

## Escalabilidade
- Separacao por camadas para manutencao simples.
- Pronto para migrar de container unico da API para multiplas replicas.
- Chaves de segmentacao ja presentes: `company_code`, `branch_code`, `terminal_code`.
- Modelo pronto para multiunidade e multicliente.
