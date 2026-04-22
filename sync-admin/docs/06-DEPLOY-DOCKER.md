# Deploy com Docker

## Description
Página legada de navegação para execução containerizada do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/deployment-and-operations.md`](./modules/deployment-and-operations.md)
- `docker-compose.yml`
- `Dockerfile`
- `nginx/default.conf`

## Integrations
- PostgreSQL
- FastAPI
- Nginx
- `scripts/init_db.py`

## Flow
1. Consulte o módulo de operações para detalhes do runtime.
2. Use esta página como atalho de navegação.

## Critical Points
- Evitar duplicar instruções de deploy.
- Preservar os comandos oficiais apenas em um local.

## Tests
- Subida do compose e verificação de health.
