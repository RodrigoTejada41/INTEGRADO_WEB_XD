#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/infra/backups}"
ENV_FILE="${ENV_FILE:-.env.prod}"

read_env() {
  local key="$1"
  local default_value="${2:-}"
  local value
  value="$(grep -E "^${key}=" "$APP_DIR/$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r' || true)"
  if [ -z "$value" ]; then
    value="$default_value"
  fi
  printf '%s' "$value"
}

BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-$(read_env BACKUP_RETENTION_DAYS 14)}"

bash "$APP_DIR/infra/scripts/backup-db.sh"
find "$BACKUP_DIR" -type f -name "postgres_*.sql.gz" -mtime +"$BACKUP_RETENTION_DAYS" -delete
echo "[backup] Rotation completed (retention ${BACKUP_RETENTION_DAYS} days)"
