# INTEGRADO WEB XD - Pipeline de Conhecimento de Engenharia Reversa

Este projeto é um pipeline modular e não monolítico que consome arquivos de conhecimento de engenharia reversa e os transforma em dados estruturados, versionados e expostos por API.

## Registro de continuidade
O ponto de retomada do projeto está em:
- [`CONTINUIDADE_PROJETO_SYNC.md`](CONTINUIDADE_PROJETO_SYNC.md)

## Protocolo de atuação
Base de resposta para outra IA ou agente:
- [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md)

## Lançamentos e registro de mudanças
- [`REGISTRO_DE_MUDANCAS.md`](REGISTRO_DE_MUDANCAS.md)
- [`NOTAS_DE_RELEASE_v0.1.0.md`](NOTAS_DE_RELEASE_v0.1.0.md)
- Tag publicada: `v0.1.0`

## Caminho principal da origem (processado pelo pipeline)
A origem de ingestão é configurada em `.env`:
- `E:\Projetos\ENGENHARIA_REVERSA\XDSoftware-Reverse-Engineering`

Use `KNOWLEDGE_SOURCE_PATHS` para alterar a pasta de origem processada.

## Referência externa de conhecimento (não processada)
`CEREBRO_VIVO` deve ser usado apenas para consulta, não para ingestão.
Use `KNOWLEDGE_REFERENCE_PATHS` somente como metadados de referência.

## Módulos
- `apps/ingestion-service`: monitora pastas de origem, indexa arquivos e cria eventos de ingestão
- `apps/reverse-engineering-service`: interpreta arquivos e infere estrutura
- `apps/transformation-service`: normaliza os dados interpretados e cria versões de dataset
- `apps/persistence-service`: grava evidências no cofre do Obsidian e nas pastas de manifestos Nexus
- `apps/api-service`: API RBAC protegida por JWT para arquivos, jobs, datasets e relatórios
- `packages/shared`: configuração compartilhada, persistência SQLite, fila de eventos e adaptadores

## Execução local
1. Crie o virtualenv e instale as dependências:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Copie o arquivo de ambiente:
```powershell
Copy-Item .env.example .env
```

## Execução rápida (lote único)
```powershell
.\scripts\run-pipeline-once.ps1
```
Isso executa a ingestão e processa todos os eventos pendentes por engenharia reversa, transformação e persistência.

## Execução contínua
```powershell
.\scripts\start-services.ps1
```
Isso abre 5 terminais e inicia todos os serviços, incluindo a API.

## Autenticação JWT, renovação e RBAC
1. Faça login e receba `access_token` + `refresh_token`:
```http
POST /auth/token
{
  "username": "admin",
  "password": "admin123"
}
```
2. Renovar sessão (rotaciona o refresh token e invalida o antigo):
```http
POST /auth/refresh
{
  "refresh_token": "<refresh_token>"
}
```
3. Encerrar sessão (revoga o access token atual e o refresh token opcional):
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

## Verificações da API
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

## Observações
- O armazenamento local usa SQLite para velocidade de desenvolvimento (`output/system.db`).
- A arquitetura é modular e pode ser migrada para PostgreSQL + broker de mensagens sem alterar as fronteiras dos serviços.
- Os dados do Obsidian são gerados como Markdown em `obsidian-vault`.
- A integração Nexus é representada por artefatos de manifesto versionados em `nexus-manifests`.

## Testes automatizados
Execute a suíte de testes em Docker:
```powershell
.\scripts\run-tests.ps1
```

Cobertura automatizada atual:
- endpoint de saúde
- login + `/api/v1/auth/me`
- enforcement de RBAC (viewer negado em `/api/v1/files`)
- rotação de refresh token (refresh antigo rejeitado)
- revogação no logout (access token inválido após logout)

## Verificação end-to-end
Execute o smoke rápido (ingestão limitada):
```powershell
.\scripts\run-smoke-check.ps1
```

Execute o smoke completo (sem limite de ingestão):
```powershell
.\scripts\run-smoke-check-full.ps1
```

Isso valida:
- ingestão a partir de `ENGENHARIA_REVERSA`
- engenharia reversa + transformação + persistência
- artefatos gerados em Obsidian e nas pastas de manifestos Nexus
- login JWT e endpoints protegidos da API

