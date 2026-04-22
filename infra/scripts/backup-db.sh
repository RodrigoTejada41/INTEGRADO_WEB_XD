#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}/backups}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "[backup] Docker Compose nao encontrado."
  exit 1
fi

cd "${APP_DIR}"
mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[backup] Arquivo ${ENV_FILE} nao encontrado."
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/postgres-${POSTGRES_DB}-${TIMESTAMP}.dump"

echo "[backup] Gerando backup em ${BACKUP_FILE}..."
${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${BACKUP_FILE}"

echo "[backup] Backup concluido."
