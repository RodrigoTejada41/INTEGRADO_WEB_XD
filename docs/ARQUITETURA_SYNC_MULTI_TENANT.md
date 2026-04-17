# Arquitetura Multi-Tenant da Sincronização

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

1. O agente local lê `vendas` do MariaDB por `data_atualizacao > checkpoint`.
2. O agente envia o lote para `POST /sync` com `X-Empresa-Id` e `X-API-Key`.
3. A API valida as credenciais da empresa.
4. A API faz UPSERT no PostgreSQL central por `(empresa_id, uuid)`.
5. O job de retenção remove ou arquiva dados com mais de 14 meses.

## Segurança

- Autenticação por API key por tenant.
- `empresa_id` validado por regex.
- SQL com parâmetros e SQLAlchemy para evitar injeção.
- Rotação de API key via endpoint administrativo com token:
  - `POST /admin/tenants`
  - `POST /admin/tenants/{empresa_id}/rotate-key`

## Observabilidade
