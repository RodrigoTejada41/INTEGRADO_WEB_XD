# API REST

## Description
Página legada de navegação para os endpoints HTTP do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/api.md`](./modules/api.md)
- [`modules/schemas.md`](./modules/schemas.md)
- `app/api/routes/`

## Integrations
- `GET /health`
- `POST /api/sync-data`
- `X-API-Key`
- Pydantic

## Flow
1. Use o módulo de API para a especificação detalhada.
2. Use esta página para navegação rápida.

## Critical Points
- O contrato verdadeiro vive nos módulos.
- Esta página não deve carregar exemplos duplicados.

## Tests
- Confirmar health, ingestão e rejeição de payloads inválidos.
