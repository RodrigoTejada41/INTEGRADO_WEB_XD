#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
REPO_URL="${REPO_URL:-https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD.git}"
BRANCH="${BRANCH:-main}"
APP_USER="${APP_USER:-$USER}"

echo "[setup] Starting VPS setup"

if ! command -v git >/dev/null 2>&1; then
  echo "[setup] Installing git"
  sudo apt-get update -y
  sudo apt-get install -y git
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[setup] Docker is required but not installed."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[setup] Docker Compose plugin is required but not installed."
  exit 1
fi

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "[setup] Cloning repository into $APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "[setup] Repository already present, fetching updates"
  git -C "$APP_DIR" fetch origin "$BRANCH"
fi

mkdir -p "$APP_DIR/runtime"
mkdir -p "$APP_DIR/infra/backups"
mkdir -p "$APP_DIR/infra/nginx/certs"
mkdir -p "$APP_DIR/infra/nginx/certbot"
mkdir -p "$APP_DIR/infra/logs"

if [ ! -f "$APP_DIR/.env.prod" ]; then
  echo "[setup] Creating .env.prod from template"
  cp "$APP_DIR/infra/env/.env.prod.example" "$APP_DIR/.env.prod"
  echo "[setup] Fill $APP_DIR/.env.prod before first deploy."
fi

chmod +x "$APP_DIR"/infra/scripts/*.sh || true

echo "[setup] VPS setup completed"
