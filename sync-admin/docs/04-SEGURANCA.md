# Segurança

## Description
Página legada de navegação para os controles de autenticação, autorização e hashing do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/core-infrastructure.md`](./modules/core-infrastructure.md)
- [`modules/web-ui.md`](./modules/web-ui.md)
- [`modules/api.md`](./modules/api.md)

## Integrations
- bcrypt
- JWT
- Session middleware
- `X-API-Key`

## Flow
1. Consulte o módulo de infraestrutura para os helpers de segurança.
2. Consulte o módulo web para sessão e autorização.
3. Use esta página como ponto de navegação.

## Critical Points
- Não duplicar regras de segurança aqui.
- O endurecimento futuro deve entrar nos módulos apropriados.

## Tests
- Login, sessão, role checks e rejeição de chave inválida.
