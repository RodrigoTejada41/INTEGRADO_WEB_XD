# Frontend README de Compatibilidade

Este diretorio e uma ponte de compatibilidade para quem espera encontrar um frontend dedicado em `frontend/`. O painel administrativo em producao continua tendo como fonte de verdade o modulo `sync-admin/`.

## Fonte de verdade

Origem principal do painel:

- `sync-admin/app/`
- `sync-admin/app/templates/`
- `sync-admin/app/static/`
- `sync-admin/app/services/`
- `sync-admin/app/api/`
- `sync-admin/app/web/`
- `sync-admin/Dockerfile`
- `sync-admin/docker-compose.yml`

Regra:
- implementacoes reais do painel, templates, assets e integracoes devem continuar em `sync-admin/`.

## Mapeamento da ponte

| Caminho esperado em `frontend/` | Fonte de verdade atual |
| --- | --- |
| `src/pages/` | `sync-admin/app/templates/`, `sync-admin/app/web/routes/` |
| `src/components/` | `sync-admin/app/templates/partials/`, `sync-admin/app/static/js/` |
| `src/services/` | `sync-admin/app/services/` |
| `src/hooks/` | `sync-admin/app/web/deps.py`, helpers de sessao e autenticacao em `sync-admin/app/services/` |
| `public/` | `sync-admin/app/static/` |

## Papel desta camada

Use `frontend/` apenas para:

- navegacao por convencao de repositorios que separam frontend na raiz;
- documentacao de compatibilidade;
- preparacao de uma migracao futura, caso ela seja oficialmente decidida.

Nao trate `frontend/` como:

- novo runtime do painel;
- substituto de `sync-admin/`;
- autorizacao implicita para duplicar templates, assets ou servicos.

## Regras preservadas

- o painel continua consumindo a API central de forma coerente com isolamento por `empresa_id`;
- as regras de autenticacao e validacao permanecem definidas pelos modulos reais;
- qualquer reorganizacao futura deve atualizar esta ponte e a documentacao central ao mesmo tempo.

## Referencia central

Para a declaracao oficial da estrutura do projeto, consulte `docs/PROJECT_STRUCTURE_SYNC.md`.
