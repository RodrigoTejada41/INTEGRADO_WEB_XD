# Sync Admin Modules

This directory contains the module-level documentation for `sync-admin`.

## Local-First Entry

1. [`../../CEREBRO_VIVO.md`](../../CEREBRO_VIVO.md)
2. [`../../.cerebro-vivo/README.md`](../../.cerebro-vivo/README.md)
3. [`../../PROTOCOLO_ESPECIALISTAS.md`](../../PROTOCOLO_ESPECIALISTAS.md)
4. [`../../CONTINUIDADE_PROJETO_SYNC.md`](../../CONTINUIDADE_PROJETO_SYNC.md)

## Module Registry

- [Application Bootstrap](./application-bootstrap.md)
- [API](./api.md)
- [Configuration](./configuration.md)
- [Core Infrastructure](./core-infrastructure.md)
- [Database and Models](./database-and-models.md)
- [Deployment and Operations](./deployment-and-operations.md)
- [Repositories](./repositories.md)
- [Schemas](./schemas.md)
- [Services](./services.md)
- [Web UI](./web-ui.md)

## File Classification

- `app/main.py` -> application bootstrap
- `app/api/**` -> API module
- `app/config/**` -> configuration module
- `app/core/**` -> core infrastructure module
- `app/models/**` -> database and models module
- `app/repositories/**` -> repositories module
- `app/schemas/**` -> schemas module
- `app/services/**` -> services module
- `app/web/**`, `app/templates/**`, `app/static/**` -> web UI module
- `docker-compose.yml`, `Dockerfile`, `nginx/default.conf`, `scripts/init_db.py`, `requirements.txt`, `VERSION` -> deployment and operations module

## Guidance

Each module document follows the same structure:

1. Description
2. Structure
3. Integrations
4. Flow
5. Critical Points
6. Tests

Use the module documents as the canonical navigation layer for the panel.
