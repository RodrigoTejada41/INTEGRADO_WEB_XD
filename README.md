# INTEGRADO WEB XD - Plataforma de Sincronizacao Multi-Tenant

Este projeto e uma plataforma modular de sincronizacao de dados multi-tenant, com agentes locais, API central em FastAPI e banco central PostgreSQL.

O foco principal do repositorio e:
- sincronizar dados novos ou atualizados em lotes;
- preservar isolamento rigoroso por `empresa_id`;
- aplicar autenticacao, auditoria e governanca em ambiente multiempresa;
- manter politica de retencao maxima de 14 meses nas tabelas principais.

## Estrutura operacional oficial

As fontes canonicas operacionais deste repositorio sao:
- `backend/`
- `agent_local/`
- `sync-admin/`
- `infra/`

Essas pastas representam a definicao principal do produto, da operacao e da governanca tecnica.

## Compatibilidade e onboarding

As seguintes estruturas permanecem como camadas de compatibilidade, transicao tecnica ou onboarding:
- `backend/src`
- `frontend`
- `database`
- `devops`
- `docker-compose.yml` na raiz

Essas camadas nao substituem a governanca das pastas canonicas operacionais e devem ser lidas como apoio de integracao, adaptacao ou entrada no workspace.

Artefatos legados ou adjacentes de conhecimento, ingestao documental e engenharia reversa permanecem como contexto de apoio ao workspace, nao como definicao primaria do produto.

## Base local-first
Este projeto usa `CEREBRO_VIVO` como base de conhecimento local-first para continuidade operacional e historico tecnico.

### Entrada recomendada
- [`CEREBRO_VIVO.md`](CEREBRO_VIVO.md)
- [`.cerebro-vivo/README.md`](.cerebro-vivo/README.md)

### Ordem de uso
1. Abra `CEREBRO_VIVO.md` na raiz do projeto.
2. Leia `.cerebro-vivo/README.md` para seguir a rotina local-first.
3. Use a web apenas depois de consultar essa base local e os indices internos.

## Registro de continuidade
O ponto de retomada do projeto esta em:
- [RETOMADA_EXATA.md](RETOMADA_EXATA.md)
- [CONTINUIDADE_PROJETO_SYNC.md](CONTINUIDADE_PROJETO_SYNC.md)

## Arquitetura principal
- agentes locais conectados a MariaDB;
- API central em FastAPI;
- banco central PostgreSQL;
- sincronizacao periodica com isolamento estrito por tenant.

## Protocolo de atuacao
Base de resposta para outra IA ou agente:
- [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md)
- [`AGENTS.md`](AGENTS.md)

## Modo oficial multi-agentes
O repositorio passa a operar oficialmente em modo multi-agentes.

Regras de coordenacao:
- `AGENTS.md` e a fonte principal de governanca, precedencia e regras criticas.
- `PROTOCOLO_ESPECIALISTAS.md` continua como base de formato e postura senior.
- Quando houver varias disciplinas na mesma tarefa, deve existir um agente lider, especialistas de apoio e revisao final cruzada.
- Nenhum fluxo multi-agentes pode violar isolamento por `empresa_id`, autenticacao, UUID de sincronizacao, modularidade ou a retencao maxima de 14 meses.

## Memoria do projeto: coexistencia entre `cerebro_vivo/` e `.cerebro-vivo/`

Este workspace agora mantem duas camadas complementares de memoria:

- [`.cerebro-vivo/README.md`](.cerebro-vivo/README.md): base operacional local-first, historica e detalhada
- [`cerebro_vivo/estado_atual.md`](cerebro_vivo/estado_atual.md): resumo executivo visivel para retomada rapida
- [`cerebro_vivo/historico_decisoes.md`](cerebro_vivo/historico_decisoes.md): decisoes consolidadas com ponte para a base detalhada
- [`cerebro_vivo/memoria_projeto.json`](cerebro_vivo/memoria_projeto.json): espelho leve do contexto atual

Regra pratica:
- use `cerebro_vivo/` para onboarding rapido, coordenacao multi-agentes e leitura executiva;
- use `.cerebro-vivo/` para trilha detalhada, logs, painel e memoria operacional historica.

## Contexto secundario e artefatos adjacentes
Este repositorio tambem abriga documentacao, indices, artefatos de apoio e trilhas historicas relacionadas a ingestao de conhecimento e engenharia reversa. Esses elementos devem ser tratados como contexto auxiliar ao trabalho principal de sincronizacao multi-tenant.

## Indice mestre da documentacao
- [`INDICE_DOCUMENTACAO_MESTRA.md`](INDICE_DOCUMENTACAO_MESTRA.md)
- [`DOCUMENTACAO.md`](DOCUMENTACAO.md)

## Indices modulares
- [`sync-admin/docs/modules/README.md`](sync-admin/docs/modules/README.md)
- [`apps/reporting-web/README.md`](apps/reporting-web/README.md)

## Lancamentos e registro de mudancas
- [`REGISTRO_DE_MUDANCAS.md`](REGISTRO_DE_MUDANCAS.md)
- [`NOTAS_DE_RELEASE_v0.1.0.md`](NOTAS_DE_RELEASE_v0.1.0.md)
- Tag publicada: `v0.1.0`

## Deploy em VPS (producao)
- Guia operacional: [`infra/VPS_DEPLOY.md`](infra/VPS_DEPLOY.md)
- Acesso SSH e handoff para outra IA: [`infra/SSH_ACESSO.md`](infra/SSH_ACESSO.md)
- Stack de producao: `docker-compose.prod.yml`
- Nginx reverso: `infra/nginx/default.conf`
- Deploy principal: `.github/workflows/deploy-prod.yml`
- Variante manual self-hosted: `.github/workflows/deploy-prod-self-hosted.yml`

## Caminho principal da origem (processado pelo pipeline)
A origem de ingestao e configurada em `.env`:
- `E:\Projetos\ENGENHARIA_REVERSA\XDSoftware-Reverse-Engineering`

Use `KNOWLEDGE_SOURCE_PATHS` para alterar a pasta de origem processada.

## Referencia externa de conhecimento (nao processada)
`CEREBRO_VIVO` deve ser usado primeiro como consulta local antes de recorrer a web.
Use `KNOWLEDGE_REFERENCE_PATHS` somente como metadados de referencia.

## Modulos
- `apps/ingestion-service`: monitora pastas de origem, indexa arquivos e cria eventos de ingestao
- `apps/reverse-engineering-service`: interpreta arquivos e infere estrutura
- `apps/transformation-service`: normaliza os dados interpretados e cria versoes de dataset
- `apps/persistence-service`: grava evidencias no cofre do Obsidian e nas pastas de manifestos Nexus
- `apps/api-service`: API RBAC protegida por JWT para arquivos, jobs, datasets e relatorios
- `packages/shared`: configuracao compartilhada, persistencia SQLite, fila de eventos e adaptadores

## Execucao local
1. Crie o virtualenv e instale as dependencias:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Copie o arquivo de ambiente:
```powershell
Copy-Item .env.example .env
```

## Execucao rapida (lote unico)
```powershell
.\scripts\run-pipeline-once.ps1
```
Isso executa a ingestao e processa todos os eventos pendentes por engenharia reversa, transformacao e persistencia.

## Execucao continua
```powershell
.\scripts\start-services.ps1
```
Isso abre 5 terminais e inicia todos os servicos, incluindo a API.

## Autenticacao JWT, renovacao e RBAC
1. Faca login e receba `access_token` + `refresh_token`:
```http
POST /auth/token
{
  "username": "admin",
  "password": "admin123"
}
```
2. Renovar sessao (rotaciona o refresh token e invalida o antigo):
```http
POST /auth/refresh
{
  "refresh_token": "<refresh_token>"
}
```
3. Encerrar sessao (revoga o access token atual e o refresh token opcional):
```http
POST /auth/logout
Authorization: Bearer <access_token>
{
  "refresh_token": "<refresh_token_optional>"
}
```
4. Use o access token nos endpoints protegidos:
```http
Authorization: Bearer <access_token>
```
5. Perfis:
- `admin`: files/jobs/datasets/reports/audit
- `analyst`: files/jobs/datasets/reports
- `viewer`: datasets/reports

## Verificacoes da API
- `GET /health`
- `POST /auth/token`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/files`
- `GET /api/v1/jobs`
- `GET /api/v1/datasets`
- `GET /api/v1/reports/summary`
- `GET /api/v1/audit-events` (admin only)

## Fluxo de dados
`source files -> ingestion -> reverse engineering -> transformation -> DB -> Nexus manifests + Obsidian notes -> API reports`

## Observacoes
- O armazenamento local usa SQLite para velocidade de desenvolvimento (`output/system.db`).
- A arquitetura e modular e pode ser migrada para PostgreSQL + broker de mensagens sem alterar as fronteiras dos servicos.
- Os dados do Obsidian sao gerados como Markdown em `obsidian-vault`.
- A integracao Nexus e representada por artefatos de manifesto versionados em `nexus-manifests`.

## Testes automatizados
Execute a suite de testes em Docker:
```powershell
.\scripts\run-tests.ps1
```

Cobertura automatizada atual:
- endpoint de saude
- login + `/api/v1/auth/me`
- enforcement de RBAC (viewer negado em `/api/v1/files`)
- rotacao de refresh token (refresh antigo rejeitado)
- revogacao no logout (access token invalido apos logout)

## Verificacao end-to-end
Execute o smoke rapido (ingestao limitada):
```powershell
.\scripts\run-smoke-check.ps1
```

Execute o smoke completo (sem limite de ingestao):
```powershell
.\scripts\run-smoke-check-full.ps1
```

Isso valida:
- ingestao a partir de `ENGENHARIA_REVERSA`
- engenharia reversa + transformacao + persistencia
- artefatos gerados em Obsidian e nas pastas de manifestos Nexus
- login JWT e endpoints protegidos da API
