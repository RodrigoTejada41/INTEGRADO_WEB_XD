#!/usr/bin/env bash
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
DEPLOY_PUBLIC_KEY="${DEPLOY_PUBLIC_KEY:-}"
DEPLOY_FROM="${DEPLOY_FROM:-}"
DEPLOY_GROUP="${DEPLOY_GROUP:-$DEPLOY_USER}"
AUTHORIZED_KEYS_PATH="/home/${DEPLOY_USER}/.ssh/authorized_keys"

if [[ -z "${DEPLOY_PUBLIC_KEY}" ]]; then
  echo "[deploy-user] Defina DEPLOY_PUBLIC_KEY com a chave publica autorizada."
  exit 1
fi

if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  echo "[deploy-user] Criando usuario ${DEPLOY_USER}..."
  sudo useradd -m -s /bin/bash "${DEPLOY_USER}"
fi

if ! getent group "${DEPLOY_GROUP}" >/dev/null 2>&1; then
  echo "[deploy-user] Criando grupo ${DEPLOY_GROUP}..."
  sudo groupadd "${DEPLOY_GROUP}"
fi

echo "[deploy-user] Preparando diretorios..."
sudo usermod -aG docker "${DEPLOY_USER}"
sudo install -d -m 700 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"
sudo touch "${AUTHORIZED_KEYS_PATH}"
sudo chown "${DEPLOY_USER}:${DEPLOY_USER}" "${AUTHORIZED_KEYS_PATH}"
sudo chmod 600 "${AUTHORIZED_KEYS_PATH}"

RESTRICTED_PREFIX='no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding'
if [[ -n "${DEPLOY_FROM}" ]]; then
  RESTRICTED_PREFIX="from=\"${DEPLOY_FROM}\",${RESTRICTED_PREFIX}"
fi

FORCED_COMMAND="command=\"/usr/bin/env APP_DIR=${APP_DIR} bash ${APP_DIR}/infra/scripts/update.sh\""
AUTHORIZED_LINE="${RESTRICTED_PREFIX},${FORCED_COMMAND} ${DEPLOY_PUBLIC_KEY}"

echo "[deploy-user] Instalando chave restrita em ${AUTHORIZED_KEYS_PATH}..."
TMP_FILE="$(mktemp)"
sudo cat "${AUTHORIZED_KEYS_PATH}" > "${TMP_FILE}" || true
grep -F -v "${DEPLOY_PUBLIC_KEY}" "${TMP_FILE}" > "${TMP_FILE}.filtered" || true
printf '%s\n' "${AUTHORIZED_LINE}" >> "${TMP_FILE}.filtered"
sudo cp "${TMP_FILE}.filtered" "${AUTHORIZED_KEYS_PATH}"
sudo chown "${DEPLOY_USER}:${DEPLOY_USER}" "${AUTHORIZED_KEYS_PATH}"
sudo chmod 600 "${AUTHORIZED_KEYS_PATH}"
rm -f "${TMP_FILE}" "${TMP_FILE}.filtered"

echo "[deploy-user] Garantindo posse do diretorio de aplicacao..."
sudo mkdir -p "${APP_DIR}"
sudo chown -R "${DEPLOY_USER}:${DEPLOY_GROUP}" "${APP_DIR}"

echo "[deploy-user] Usuario de deploy preparado com comando restrito."
