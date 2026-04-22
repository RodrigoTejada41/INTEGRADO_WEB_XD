# Database README de Compatibilidade

Este diretorio concentra pontos de descoberta para quem procura ativos de banco em `database/`, mas a implementacao real de schema e evolucao de banco continua distribuida nas fontes canonicas do projeto.

## Fontes de verdade

Origem principal:

- `backend/db/migrations/`
- `backend/db/migration_runner.py`
- `backend/sql/postgresql_schema.sql`
- `infra/sql/schema.sql`

Regra:
- migrations, schema operacional e mudancas estruturais devem ser mantidos nas origens acima.

## Papel desta camada

Use `database/` para:

- facilitar onboarding e descoberta;
- expor espelhos ou referencias de compatibilidade;
- registrar o mapeamento entre o caminho esperado e os ativos reais.

Nao use `database/` como:

- substituto do fluxo oficial de migrations;
- unica referencia de schema;
- criterio para ignorar `backend/db/`, `backend/sql/` ou `infra/sql/`.

## Mapeamento de compatibilidade

| Artefato em `database/` | Papel | Fonte de verdade associada |
| --- | --- | --- |
| `schema.sql` | espelho de compatibilidade para consulta humana | `backend/sql/postgresql_schema.sql` e `infra/sql/schema.sql` |
| `migrations/` | ponto de organizacao por convencao | `backend/db/migrations/` |
| `seeds/` | area reservada para apoio e bootstrap documental | definir junto da origem canonica correspondente quando houver uso real |

## Regras que permanecem obrigatorias

- isolamento multi-tenant por `empresa_id`;
- registros de sync com `uuid`, `empresa_id` e `data_atualizacao`;
- gravacoes com semantica de upsert;
- retencao maxima de 14 meses nas tabelas principais;
- preferencia por estrategia de retencao e particionamento definida na implementacao real.

## Referencia central

Para a declaracao oficial da estrutura do projeto, consulte `docs/PROJECT_STRUCTURE_SYNC.md`.
