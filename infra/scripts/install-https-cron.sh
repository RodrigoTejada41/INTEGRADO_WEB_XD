#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
CRON_FILE="/etc/cron.d/integrado-https"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 2 * * * root APP_DIR=$APP_DIR bash $APP_DIR/infra/scripts/renew-certificates.sh
EOF

chmod 644 "$CRON_FILE"
echo "[https] Installed renewal cron at $CRON_FILE"
