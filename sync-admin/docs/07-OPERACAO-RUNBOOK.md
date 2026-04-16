# Runbook Operacional

## Operacao diaria
1. Verificar health endpoint.
2. Verificar ultimos lotes no dashboard.
3. Verificar falhas em `/history`.
4. Exportar CSV quando necessario.

## Comandos uteis
```powershell
docker compose --env-file .env ps
docker compose --env-file .env logs api --tail 200
docker compose --env-file .env logs web --tail 200
docker compose --env-file .env logs db --tail 200
```

## Backup
- Banco: dump diario do PostgreSQL.
- Configuracao: versionar `docker-compose.yml`, `nginx/default.conf`, docs.

## Recuperacao
1. Restaurar dump no PostgreSQL.
2. Reaplicar `.env`.
3. Rebuild e subida com `docker compose up -d --build`.
