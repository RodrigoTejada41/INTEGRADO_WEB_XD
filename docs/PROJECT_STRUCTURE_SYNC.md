# Estrutura Canonica do Projeto de Sincronizacao

> Documento normativo para navegacao do repositorio de sincronizacao multi-tenant. Em caso de duvida sobre onde implementar, manter ou consultar uma capacidade, este arquivo define a estrutura canonica e o papel das camadas de compatibilidade.

## Objetivo

Formalizar:

- qual estrutura e canonica para o produto de sincronizacao;
- quais diretorios existem como fonte de verdade operacional;
- quais diretorios existem como ponte de compatibilidade e navegacao;
- como evitar duplicidade documental e decisao em diretorio errado.

## Principios de governanca

- O produto principal deste repositorio e a plataforma de sincronizacao multi-tenant.
- A implementacao canonica nao deve ser inferida apenas por nomes de pastas de compatibilidade.
- Camadas de compatibilidade nao substituem entrypoints, migrations, schemas ou ativos operacionais reais.
- Regras criticas continuam obrigatorias em qualquer estrutura:
  - isolamento por `empresa_id`;
  - identificacao global por `uuid`;
  - uso de `data_atualizacao` nas rotinas de sync;
  - retencao maxima de 14 meses nas tabelas principais;
  - autenticacao e validacao por tenant.

## Mapa canonico

### 1. Backend da API central

Fonte de verdade: `backend/`

Responsabilidades canonicas:

- `backend/main.py`: entrypoint da aplicacao FastAPI
- `backend/api/`: rotas HTTP, dependencias de API e fronteira de entrada
- `backend/services/`: regras de negocio, orchestracao de sync, retencao e administracao
- `backend/repositories/`: acesso a dados e queries encapsuladas
- `backend/models/`: modelos ORM
- `backend/schemas/`: contratos de entrada e saida
- `backend/config/`: configuracoes
- `backend/db/`: runner e migrations Python
- `backend/sql/`: schema SQL de referencia do backend
- `backend/utils/`: utilitarios transversais

Observacao:
- `backend/src/` nao e a implementacao principal. Ele existe como camada de compatibilidade documental para equipes que esperam uma arvore `src/` explicita.

### 2. Frontend administrativo

Fonte de verdade: `sync-admin/`

Responsabilidades canonicas:

- `sync-admin/app/`: aplicacao web administrativa
- `sync-admin/app/templates/`: telas e composicao HTML
- `sync-admin/app/static/`: assets estaticos
- `sync-admin/app/services/`: servicos usados pelo painel
- `sync-admin/app/api/` e `sync-admin/app/web/`: integracao, rotas e dependencias do painel
- `sync-admin/Dockerfile` e `sync-admin/docker-compose.yml`: ativos locais do painel

Observacao:
- `frontend/` nao substitui `sync-admin/`. Ele funciona como ponte de compatibilidade para navegacao e alinhamento com estruturas esperadas por outras equipes.

### 3. Banco de dados central

Fontes de verdade:

- `backend/db/`: migrations e orquestracao de evolucao de banco
- `backend/sql/postgresql_schema.sql`: schema SQL de referencia do backend
- `infra/sql/schema.sql`: schema SQL de referencia para operacao e deploy

Responsabilidades canonicas:

- evolucao do schema via migrations do backend;
- definicao estrutural das tabelas principais e de arquivo;
- preservacao das regras de multi-tenant, upsert e retencao.

Observacao:
- `database/` centraliza acessos de compatibilidade e consulta humana. Nao substitui o fluxo real de migrations nem o schema de referencia operacional.

### 4. Operacao e entrega

Fontes de verdade:

- `infra/`: ativos executaveis de operacao, scripts, nginx e SQL de suporte
- `docker-compose.prod.yml`: composicao de producao publicada na raiz
- `.github/workflows/`: automacoes versionadas do repositorio

Responsabilidades canonicas:

- deploy;
- configuracao operacional;
- artefatos de infraestrutura;
- automacao de entrega.

Observacao:
- `devops/` e uma camada de navegacao e compatibilidade documental. Nao passa a ser a origem de scripts, workflows ou manifests operacionais.

## Camadas de compatibilidade

As pastas abaixo existem para reduzir atrito de onboarding, busca por convencao conhecida e futura migracao gradual. Elas devem ser tratadas como ponte, nao como fonte primaria:

| Diretorio | Papel | Regra pratica |
| --- | --- | --- |
| `backend/src/` | espelho conceitual da arquitetura em camadas | documentar e mapear para `backend/` |
| `frontend/` | entrada de compatibilidade para quem procura um frontend dedicado | apontar para `sync-admin/` |
| `database/` | ponto de descoberta para ativos de banco | apontar para `backend/db/`, `backend/sql/` e `infra/sql/` |
| `devops/` | ponto de navegacao operacional | apontar para `infra/`, raiz de deploy e workflows |

## Regra de decisao rapida

Use esta heuristica antes de alterar qualquer artefato:

1. Se o artefato executa em runtime, procure primeiro a fonte canonica.
2. Se o diretorio foi criado para compatibilidade, documente, mapeie ou encaminhe; nao promova automaticamente para origem de execucao.
3. Se houver duplicidade entre ponte e origem, a origem canonica prevalece.
4. Se uma futura migracao mover a implementacao real, este documento e os READMEs de compatibilidade devem ser atualizados juntos.

## Tabela resumida de fonte de verdade

| Dominio | Fonte de verdade atual | Ponte de compatibilidade |
| --- | --- | --- |
| API central | `backend/` | `backend/src/` |
| Painel web | `sync-admin/` | `frontend/` |
| Schema e migrations | `backend/db/`, `backend/sql/`, `infra/sql/` | `database/` |
| Deploy e operacao | `infra/`, `.github/workflows/`, `docker-compose.prod.yml` | `devops/` |

## Impacto esperado

Esta definicao reduz ambiguidades sobre onde:

- implementar novas capacidades;
- revisar seguranca, retencao e multi-tenant;
- procurar artefatos operacionais reais;
- manter a camada de compatibilidade sem deslocar o produto para uma estrutura ainda nao migrada.

## Referencias relacionadas

- `AGENTS.md`
- `PROTOCOLO_ESPECIALISTAS.md`
- `docs/ARQUITETURA_SYNC_MULTI_TENANT.md`
- `backend/src/README.md`
- `frontend/README.md`
- `database/README.md`
- `devops/README.md`
