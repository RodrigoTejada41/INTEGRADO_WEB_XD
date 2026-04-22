# Fluxograma Atual

## Description
Página legada de navegação para os fluxos do `sync-admin`.

## Structure
- [`modules/api.md`](./modules/api.md)
- [`modules/web-ui.md`](./modules/web-ui.md)
- [`modules/services.md`](./modules/services.md)

## Integrations
- Sync API
- Painel web
- Banco de dados

## Flow
1. O lote entra pela API.
2. O painel consome o estado agregado.
3. O usuário navega pelas telas administrativas.

## Critical Points
- O fluxograma detalhado deve ficar em um só ponto.
- Esta página deve apenas encaminhar para os módulos.

## Tests
- Conferir consistência com API, UI e serviços.
