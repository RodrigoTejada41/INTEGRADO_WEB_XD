# Deploy com Docker

## Arquivos
- `Dockerfile`
- `docker-compose.yml`
- `nginx/default.conf`

## Servicos
- `db` -> PostgreSQL
- `api` -> FastAPI
- `web` -> Nginx

## Subida local
```powershell
cd sync-admin
Copy-Item .env.example .env
docker compose --env-file .env up -d --build
```

## Verificacao
```powershell
docker compose --env-file .env ps
```

## Acesso
- Painel: `http://localhost:8080/login`
- Health: `http://localhost:8080/health`

## Variaveis sensiveis
Configurar no `.env`:
- `SECRET_KEY`
- `DATABASE_URL`
- `INITIAL_ADMIN_PASSWORD`
- `INTEGRATION_API_KEY`
