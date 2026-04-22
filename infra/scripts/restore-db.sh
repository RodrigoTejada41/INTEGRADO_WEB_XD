#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_FILE="${1:-}"

if [[ -z "${BACKUP_FILE}" ]]; then
  echo "Uso: bash infra/scripts/restore-db.sh /caminho/backup.dump"
  exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "[restore] Backup nao encontrado: ${BACKUP_FILE}"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "[restore] Docker Compose nao encontrado."
  exit 1
fi

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[restore] Arquivo ${ENV_FILE} nao encontrado."
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

echo "[restore] Isso ira sobrescrever o banco ${POSTGRES_DB}. Digite YES para continuar:"
read -r CONFIRM
if [[ "${CONFIRM}" != "YES" ]]; then
  echo "[restore] Operacao cancelada."
  exit 0
fi

echo "[restore] Restaurando backup..."
cat "${BACKUP_FILE}" | ${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_restore --clean --if-exists -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "[restore] Restore concluido."
