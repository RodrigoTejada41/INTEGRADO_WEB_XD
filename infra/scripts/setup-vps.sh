#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
APP_USER="${APP_USER:-$USER}"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"

echo "[setup] APP_DIR=${APP_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[setup] Docker nao encontrado. Instale Docker antes de continuar."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "[setup] Docker Compose nao encontrado."
  exit 1
fi

echo "[setup] Compose detectado: ${COMPOSE_CMD}"

sudo mkdir -p "${APP_DIR}" "${APP_DIR}/backups" "${APP_DIR}/logs"
sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

if [[ -n "${REPO_URL}" && ! -d "${APP_DIR}/.git" ]]; then
  echo "[setup] Clonando repositorio..."
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "[setup] Repositorio nao encontrado em ${APP_DIR}."
  echo "[setup] Defina REPO_URL para clone automatico ou copie o projeto manualmente."
  exit 1
fi

cd "${APP_DIR}"

if [[ ! -f ".env.prod" ]]; then
  cp .env.prod.example .env.prod
  echo "[setup] Arquivo .env.prod criado a partir de .env.prod.example."
  echo "[setup] Edite .env.prod com valores de producao antes do deploy."
fi

echo "[setup] Estrutura da VPS preparada com sucesso."
