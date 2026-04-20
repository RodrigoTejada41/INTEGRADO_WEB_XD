#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/infra/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

bash "$APP_DIR/infra/scripts/backup-db.sh"
find "$BACKUP_DIR" -type f -name "postgres_*.sql.gz" -mtime +"$BACKUP_RETENTION_DAYS" -delete
echo "[backup] Rotation completed (retention ${BACKUP_RETENTION_DAYS} days)"
