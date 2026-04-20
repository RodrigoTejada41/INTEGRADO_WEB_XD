#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "[cert-renew] Missing $ENV_FILE"
  exit 1
fi

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

DOMAIN="$(read_env DOMAIN)"
LETSENCRYPT_EMAIL="$(read_env LETSENCRYPT_EMAIL)"

if [ -z "${DOMAIN:-}" ] || [ -z "${LETSENCRYPT_EMAIL:-}" ]; then
  echo "[cert-renew] DOMAIN and LETSENCRYPT_EMAIL are required in $ENV_FILE"
  exit 1
fi

mkdir -p infra/nginx/certbot
mkdir -p infra/nginx/certs

docker run --rm \
  -v "$APP_DIR/infra/nginx/certs:/etc/letsencrypt" \
  -v "$APP_DIR/infra/nginx/certbot:/var/www/certbot" \
  certbot/certbot renew --webroot --webroot-path /var/www/certbot --quiet

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T nginx nginx -s reload
echo "[cert-renew] Certificates renewed/reloaded"
