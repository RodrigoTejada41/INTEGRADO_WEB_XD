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

set -a
source "$ENV_FILE"
set +a

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
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

echo "[https] Switching nginx to HTTPS config"
DOMAIN="$DOMAIN" envsubst '${DOMAIN}' < infra/nginx/default.https.template.conf > infra/nginx/default.conf
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d nginx

echo "[https] HTTPS enabled for $DOMAIN"
