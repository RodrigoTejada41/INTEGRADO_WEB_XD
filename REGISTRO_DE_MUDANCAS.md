# Registro de Mudancas

## v0.3.0 - Em andamento

### Entregue
- Prioridades `1` a `18` concluidas.
- Backend com scheduler persistido por tenant, worker pool, retry por classe de falha, DLQ, backpressure por tenant e auditoria.
- Observabilidade base e operacional: health/live/ready, metrics, request id, response time e rate limit local.
- Observabilidade avancada por tenant: contadores por `empresa_id`, lag por tenant, endpoint admin tipado e painel atualizado.
- Correlacao de logs ponta a ponta: `correlation_id` no middleware, scheduler, worker e auditoria.
- Hardening base: validacao de credenciais, configuracoes de seguranca e politicas iniciais.
- `sync-admin` com RBAC, filtros por empresa/filial/terminal e exportacoes `CSV/XLSX/PDF/Markdown`.
- API de memoria do `cerebro_vivo` concluida com persistencia em DB separado + backup JSON.
- Snapshot local-first em `.cerebro-vivo/Conhecimento/hubs/sync-admin/snapshot.md`.
- Etapa extra VPS concluida no codigo: `docker-compose.prod.yml`, Nginx reverso, scripts `setup/deploy/update/backup/restore`, workflow `.github/workflows/deploy-prod.yml`, guia `infra/VPS_DEPLOY.md`.
- Suite estabilizada com `28 passed`.

### Planejado
- `P19`: governanca de segredos e auditoria expandida.
- `P20`: refinamento final de produto e operacao.
- Operacional: executar deploy real na VPS e validar health/checks via Nginx.

## v0.1.0 - Base inicial
- API central + agente local + painel administrativo.
- Retention de 14 meses.
- Isolamento multi-tenant por `empresa_id`.
