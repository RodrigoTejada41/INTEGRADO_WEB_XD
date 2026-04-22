# Banco de Dados

## Description
Página legada de navegação para a documentação de banco de dados do `sync-admin`.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`modules/database-and-models.md`](./modules/database-and-models.md)
- [`modules/repositories.md`](./modules/repositories.md)
- `app/models/`
- `app/repositories/`

## Integrations
- PostgreSQL 16
- SQLAlchemy 2.x
- Schema bootstrap no startup

## Flow
1. Consulte o módulo de modelos para o domínio persistente.
2. Consulte o módulo de repositórios para as consultas.
3. Use esta página apenas como ponte de navegação.

## Critical Points
- Não duplicar o esquema aqui.
- Não reexplicar o que já está nos módulos.

## Tests
- Verificar persistência via integração e cobertura de repositórios.
