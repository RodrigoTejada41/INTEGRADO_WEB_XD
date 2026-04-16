# Monitoramento e Logs

## Eventos registrados
- Recebimento de lote (`sync_ingested`).
- Falha de autenticacao de integracao (`sync_auth_failed`).
- Falhas de ingestao (`sync_ingest_failed`).

## Metricas recomendadas
- lotes por hora
- registros por hora
- taxa de falhas
- latencia de ingestao
- tempo sem novo recebimento

## Alerta recomendado
- Sem recebimento por > 30 minutos.
- Taxa de falha > 5% em 15 minutos.

## Proxima evolucao
- Exportar logs para stack observability (ELK/Loki/Datadog).
- Endpoint de metricas Prometheus.
