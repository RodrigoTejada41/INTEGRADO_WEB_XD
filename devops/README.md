# DevOps README de Compatibilidade

Esta pasta e uma ponte de navegacao para operacao e entrega. Os ativos executaveis e a fonte de verdade operacional continuam fora daqui, principalmente em `infra/`, na raiz do repositorio e em `.github/workflows/`.

## Fontes de verdade

Origem principal:

- `infra/nginx/`
- `infra/scripts/`
- `infra/sql/` quando houver dependencia operacional de banco
- `infra/VPS_DEPLOY.md`
- `docker-compose.prod.yml`
- `.github/workflows/`

Regra:
- scripts, manifests, rotinas de deploy e workflows reais devem continuar nas origens acima.

## Mapeamento da ponte

| Caminho em `devops/` | Papel | Fonte de verdade atual |
| --- | --- | --- |
| `nginx/` | navegacao e referencia | `infra/nginx/` |
| `scripts/` | navegacao e referencia | `infra/scripts/` |
| `deploy/` | organizacao documental de operacao | `docker-compose.prod.yml`, `infra/VPS_DEPLOY.md` e `.github/workflows/` |

## Papel desta camada

Use `devops/` para:

- orientar descoberta de ativos operacionais;
- documentar o mapeamento entre convencao esperada e estrutura real;
- apoiar onboarding sem deslocar a infraestrutura publicada.

Nao use `devops/` como:

- nova origem de scripts executaveis;
- substituto de `infra/`;
- justificativa para duplicar workflows ou configuracoes.

## Regras preservadas

- qualquer ajuste operacional deve continuar respeitando isolamento multi-tenant e seguranca por tenant;
- alteracoes que atinjam deploy ou banco precisam manter a retencao maxima de 14 meses e os controles de autenticacao ja definidos pelo produto;
- se a estrutura operacional real mudar, esta ponte deve ser atualizada junto com `docs/PROJECT_STRUCTURE_SYNC.md`.

## Referencia central

Para a declaracao oficial da estrutura do projeto, consulte `docs/PROJECT_STRUCTURE_SYNC.md`.
