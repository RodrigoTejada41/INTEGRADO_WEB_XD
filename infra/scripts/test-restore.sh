#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/infra/backups}"
TMP_CONTAINER="integrado_restore_test"
TMP_DB="restore_test"

latest_backup="$(ls -1t "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | head -n 1 || true)"
if [ -z "$latest_backup" ]; then
  echo "[restore-test] No backup file found in $BACKUP_DIR"
  exit 1
fi

echo "[restore-test] Testing restore using $latest_backup"
docker rm -f "$TMP_CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$TMP_CONTAINER" -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB="$TMP_DB" postgres:16-alpine >/dev/null

cleanup() {
  docker rm -f "$TMP_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if docker exec "$TMP_CONTAINER" pg_isready -U postgres -d "$TMP_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

gzip -dc "$latest_backup" | docker exec -i "$TMP_CONTAINER" psql -U postgres -d postgres >/dev/null
docker exec "$TMP_CONTAINER" psql -U postgres -d postgres -c "SELECT 1;" >/dev/null
echo "[restore-test] Restore test succeeded"
