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

read_env() {
  local key="$1"
  local default_value="${2:-}"
  local value
  value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r' || true)"
  if [ -z "$value" ]; then
    value="$default_value"
  fi
  printf '%s' "$value"
}

POSTGRES_USER="$(read_env POSTGRES_USER sync_user)"

echo "[backup] Creating backup at $BACKUP_FILE"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  pg_dumpall -U "$POSTGRES_USER" | gzip > "$BACKUP_FILE"

echo "[backup] Backup completed"
