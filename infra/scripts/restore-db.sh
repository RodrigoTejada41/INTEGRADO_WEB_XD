#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 /path/to/postgres_backup.sql.gz"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "[restore] Backup file not found: $BACKUP_FILE"
  exit 1
fi

cd "$APP_DIR"

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

echo "[restore] Restoring database from $BACKUP_FILE"
gzip -dc "$BACKUP_FILE" | docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  psql -U "$POSTGRES_USER" -d postgres

echo "[restore] Restore completed"
