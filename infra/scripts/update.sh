#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"

echo "[update] Fetching latest code from $BRANCH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[update] Running production deploy"
bash infra/scripts/deploy-prod.sh

echo "[update] Update completed"
