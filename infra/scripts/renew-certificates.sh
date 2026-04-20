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

set -a
source "$ENV_FILE"
set +a

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
