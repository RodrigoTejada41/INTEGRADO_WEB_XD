# Sync Multi-Tenant Architecture

## Estrutura

```text
/backend
  /api
  /services
  /repositories
  /models
  /schemas
  /config
  /utils
  /sql

/agent_local
  /db
  /sync
  /config
  /data
```

## Fluxo

1. Agente local lê `vendas` do MariaDB por `data_atualizacao > checkpoint`.
2. Agente envia lote para `POST /sync` com `X-Empresa-Id` e `X-API-Key`.
3. API valida credenciais da empresa.
4. API faz UPSERT no PostgreSQL central por `(empresa_id, uuid)`.
5. Job de retenção remove/arquiva dados com mais de 14 meses.

## Segurança

- Autenticação por API key por tenant.
- `empresa_id` validado por regex.
- SQL com parâmetros e SQLAlchemy para evitar injection.
- Rotação de API key via endpoint admin com token:
  - `POST /admin/tenants`
  - `POST /admin/tenants/{empresa_id}/rotate-key`

## Observabilidade

- Endpoint Prometheus: `GET /metrics`
- Health API: `GET /health`
- Agente local executa preflight por ciclo:
  - ping MariaDB
  - check `GET /health` da API

## Execução

### API

```bash
uvicorn backend.main:app --reload
```

### Agente local

```bash
python -m agent_local.main
```

### Docker (PostgreSQL + API + Agente)

```bash
docker compose -f infra/docker/docker-compose.sync.yml up -d --build
```

Se o MariaDB estiver no host local, o agente usa:

- `AGENT_MARIADB_URL=mysql+pymysql://root:root@host.docker.internal:3308/xd`
- `AGENT_SOURCE_QUERY` para mapear sua origem real (ex.: `salesdocumentsreportview`) para o contrato `uuid/produto/valor/data/data_atualizacao`

Se der erro de conexão `10061`, o MariaDB local não está ativo ou não está escutando em `3308`.
