# Backend/src README de Compatibilidade

Este diretorio e uma ponte de compatibilidade para quem espera uma estrutura `backend/src/` com camadas explicitas. A implementacao canonica da API central continua em `backend/`.

## Fonte de verdade

Origem principal:

- `backend/main.py`
- `backend/api/`
- `backend/services/`
- `backend/repositories/`
- `backend/models/`
- `backend/schemas/`
- `backend/config/`
- `backend/db/`
- `backend/sql/`
- `backend/utils/`

Regra:
- alteracoes executaveis devem ser feitas na estrutura acima, nao nesta arvore de compatibilidade.

## Mapeamento da ponte

| Caminho em `backend/src/` | Fonte de verdade atual |
| --- | --- |
| `controllers/` | `backend/api/routes/` |
| `routes/` | `backend/api/routes/` |
| `services/` | `backend/services/` |
| `repositories/` | `backend/repositories/` |
| `models/` | `backend/models/` |
| `config/` | `backend/config/` |
| `middlewares/` | `backend/main.py`, `backend/api/deps.py`, `backend/api/admin_deps.py`, `backend/utils/` |

## Papel desta camada

Use `backend/src/` apenas para:

- documentacao de compatibilidade;
- onboarding de equipes que buscam uma convencao `src/`;
- adaptadores ou migracao gradual futura, quando explicitamente planejados.

Nao use `backend/src/` como:

- entrypoint da aplicacao;
- origem oficial de rotas;
- origem de services, repositories ou models em runtime.

## Garantias que esta ponte deve respeitar

- isolamento multi-tenant por `empresa_id`;
- identificacao por `uuid` nas rotinas de sincronizacao;
- uso de upsert nas gravacoes;
- retencao maxima de 14 meses controlada pelos servicos e migrations reais;
- ausencia de duplicacao contraditoria com `backend/`.

## Referencia central

Para a declaracao oficial da estrutura do projeto, consulte `docs/PROJECT_STRUCTURE_SYNC.md`.
