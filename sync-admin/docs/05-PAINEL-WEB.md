# Painel Web

## Description
Página legada de navegação para a interface administrativa do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/web-ui.md`](./modules/web-ui.md)
- `app/web/routes/pages.py`
- `app/templates/`
- `app/static/`

## Integrations
- Jinja2
- Session middleware
- Dashboard service
- Control service

## Flow
1. Use o módulo web para detalhes da UI.
2. Use esta página como ponte documental.

## Critical Points
- Não repetir a descrição das telas aqui.
- Preservar a navegação entre painel, registros e configurações.

## Tests
- Login, dashboard, records, history e settings.
