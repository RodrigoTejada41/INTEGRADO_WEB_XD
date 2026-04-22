#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "[deploy] Docker Compose nao encontrado."
  exit 1
fi

wait_for_container_health() {
  local container_name="$1"
  local timeout_seconds="$2"
  local elapsed=0
  local status=""

  while (( elapsed < timeout_seconds )); do
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_name}" 2>/dev/null || true)"

    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      echo "[deploy] Container ${container_name} status=${status}"
      return 0
    fi

    if [[ "${status}" == "unhealthy" || "${status}" == "exited" || "${status}" == "dead" ]]; then
      echo "[deploy] Container ${container_name} status=${status}"
      return 1
    fi

    sleep 5
    elapsed=$((elapsed + 5))
  done

  echo "[deploy] Timeout aguardando saude de ${container_name}. Ultimo status=${status:-desconhecido}"
  return 1
}

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] Arquivo ${ENV_FILE} nao encontrado."
  exit 1
fi

echo "[deploy] Build + up do ambiente de producao..."
${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" pull --ignore-pull-failures || true
${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" build --pull
${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --remove-orphans

echo "[deploy] Executando migracoes de banco..."
${COMPOSE_CMD} --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm backend python scripts/db_migrate.py

echo "[deploy] Validando saude do ambiente..."
wait_for_container_health "integrado-backend" "${HEALTH_TIMEOUT_SECONDS}"
wait_for_container_health "integrado-frontend" "${HEALTH_TIMEOUT_SECONDS}"
wait_for_container_health "integrado-nginx" "${HEALTH_TIMEOUT_SECONDS}"
curl --fail --silent --show-error http://127.0.0.1/healthz >/dev/null
curl --fail --silent --show-error http://127.0.0.1/readyz/backend >/dev/null
curl --fail --silent --show-error http://127.0.0.1/readyz/sync-admin >/dev/null
curl --fail --silent --show-error http://127.0.0.1/api/health/ready >/dev/null

echo "[deploy] Deploy concluido com sucesso."
