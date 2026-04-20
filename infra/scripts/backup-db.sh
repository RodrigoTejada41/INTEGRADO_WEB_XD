#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/infra/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"

set -a
source "$ENV_FILE"
set +a

echo "[backup] Creating backup at $BACKUP_FILE"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  pg_dumpall -U "$POSTGRES_USER" | gzip > "$BACKUP_FILE"

echo "[backup] Backup completed"
