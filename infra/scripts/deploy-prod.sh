#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy] Missing $ENV_FILE in $APP_DIR"
  exit 1
fi

echo "[deploy] Pulling latest images (if any)"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull || true

echo "[deploy] Building and starting containers"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "[deploy] Waiting for service health checks"
sleep 10

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo "[deploy] Validating backend and nginx health"
curl -fsS http://127.0.0.1/healthz >/dev/null
curl -fsS http://127.0.0.1/api/health >/dev/null

echo "[deploy] Production deploy finished successfully"
