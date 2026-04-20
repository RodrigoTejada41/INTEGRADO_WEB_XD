#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd_dev}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.dev}"

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy-dev] Missing $ENV_FILE in $APP_DIR"
  exit 1
fi

echo "[deploy-dev] Pulling images"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull || true

echo "[deploy-dev] Building and starting containers"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans

sleep 10
echo "[deploy-dev] Running migrations and seeds"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python -m backend.scripts.migrate
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python -m backend.scripts.seed
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
curl -fsS http://127.0.0.1/healthz >/dev/null
curl -fsS http://127.0.0.1/api/health >/dev/null
echo "[deploy-dev] Dev deploy finished successfully"
