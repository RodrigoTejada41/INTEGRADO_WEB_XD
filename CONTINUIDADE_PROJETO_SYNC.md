# Continuidade do Projeto Sync

Ultima atualizacao: 2026-04-19 20:45:00 -03:00
Projeto: `INTEGRADO_WEB_XD`

## Entrada obrigatoria
- Ler primeiro [`CEREBRO_VIVO.md`](CEREBRO_VIVO.md)
- Depois ler [`RETOMADA_EXATA.md`](RETOMADA_EXATA.md)
- Seguir [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md)

## Estado atual consolidado
- Prioridades `1` a `18` implementadas no codigo.
- Backend com scheduler persistido, worker pool, retry por classe de falha, DLQ, backpressure por tenant, auditoria, observabilidade e hardening base.
- `sync-admin` com RBAC, filtros por empresa/filial/terminal e exportacao `CSV/XLSX/PDF/Markdown`.
- API de memoria (`cerebro_vivo`) ativa com escrita/leitura e persistencia em DB dedicado + backup JSON.
- Health/readiness de producao ativo no backend e no `sync-admin`.
- Snapshot local-first gerado em `.cerebro-vivo/Conhecimento/hubs/sync-admin/snapshot.md`.
- Correlacao ponta a ponta com `X-Correlation-Id` em middleware/logs/scheduler/worker/auditoria.
- Endpoint admin de observabilidade por tenant: `/admin/tenants/{empresa_id}/observability`.
- Etapa extra VPS criada: stack de producao, Nginx reverso, scripts operacionais e GitHub Actions deploy SSH.
- Suite de testes validada em `2026-04-19` com `28 passed`.

## Comando de validacao usado
```powershell
py -3 -m pytest -q
```

## Fonte de verdade para retomada
- Documento operacional unico: [`RETOMADA_EXATA.md`](RETOMADA_EXATA.md)

## Ponto pendente imediato
- Executar deploy real na VPS com `infra/VPS_DEPLOY.md`.
- Configurar secrets do GitHub Actions para liberar deploy automatico da `main`.
- Se a sessao for interrompida agora, retomar por `RETOMADA_EXATA.md` e `cerebro_vivo/estado_atual.md` antes de tomar qualquer decisao tecnica.
