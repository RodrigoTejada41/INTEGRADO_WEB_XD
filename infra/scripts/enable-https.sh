#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "[https] Missing $ENV_FILE"
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
ENABLE_WWW_DOMAIN="$(read_env ENABLE_WWW_DOMAIN false)"

if [ -z "${DOMAIN:-}" ] || [ -z "${LETSENCRYPT_EMAIL:-}" ]; then
  echo "[https] DOMAIN and LETSENCRYPT_EMAIL are required in $ENV_FILE"
  exit 1
fi

mkdir -p infra/nginx/certbot
mkdir -p infra/nginx/certs

echo "[https] Ensuring HTTP config for ACME challenge"
cp infra/nginx/default.http.conf infra/nginx/default.conf
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d nginx

echo "[https] Requesting Let's Encrypt certificate for $DOMAIN"
cert_domains=(-d "$DOMAIN")
server_names="$DOMAIN"
if [ "$ENABLE_WWW_DOMAIN" = "true" ]; then
  cert_domains+=(-d "www.$DOMAIN")
  server_names="$DOMAIN www.$DOMAIN"
fi

docker run --rm \
  -v "$APP_DIR/infra/nginx/certs:/etc/letsencrypt" \
  -v "$APP_DIR/infra/nginx/certbot:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$LETSENCRYPT_EMAIL" \
  --agree-tos \
  --non-interactive \
  --keep-until-expiring \
  "${cert_domains[@]}"

echo "[https] Switching nginx to HTTPS config"
DOMAIN="$DOMAIN" SERVER_NAMES="$server_names" envsubst '${DOMAIN} ${SERVER_NAMES}' < infra/nginx/default.https.template.conf > infra/nginx/default.conf
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --force-recreate nginx

echo "[https] HTTPS enabled for $DOMAIN"
