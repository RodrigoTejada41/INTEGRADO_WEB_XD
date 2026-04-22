# Arquitetura

## Description
Página legada de navegação para a documentação de arquitetura do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/application-bootstrap.md`](./modules/application-bootstrap.md)
- [`modules/api.md`](./modules/api.md)
- [`modules/services.md`](./modules/services.md)
- [`modules/database-and-models.md`](./modules/database-and-models.md)
- [`modules/web-ui.md`](./modules/web-ui.md)

## Integrations
- PostgreSQL
- FastAPI
- Nginx
- Session middleware

## Flow
1. Use o hub modular para a visão detalhada.
2. Consulte a arquitetura raiz quando precisar de contexto macro.
3. Mantenha esta página apenas como ponto de navegação.

## Critical Points
- A documentação detalhada vive nos módulos.
- Esta página não deve duplicar o conteúdo dos módulos.

## Tests
- Verificação documental: confirmar que o hub modular cobre este domínio.
