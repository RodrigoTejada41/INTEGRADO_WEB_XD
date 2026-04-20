#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
BRANCH="${BRANCH:-main}"
TARGET_ENV="${TARGET_ENV:-prod}"

cd "$APP_DIR"

echo "[update] Fetching latest code from $BRANCH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ "$TARGET_ENV" = "dev" ]; then
  echo "[update] Running dev deploy"
  bash infra/scripts/deploy-dev.sh
else
  echo "[update] Running production deploy"
  bash infra/scripts/deploy-prod.sh
fi

echo "[update] Update completed"
