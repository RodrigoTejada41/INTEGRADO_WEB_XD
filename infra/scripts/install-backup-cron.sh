#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
CRON_FILE="/etc/cron.d/integrado-backup"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 3 * * * root APP_DIR=$APP_DIR bash $APP_DIR/infra/scripts/backup-rotate.sh
30 3 * * 0 root APP_DIR=$APP_DIR bash $APP_DIR/infra/scripts/test-restore.sh
EOF

chmod 644 "$CRON_FILE"
echo "[backup] Installed cron at $CRON_FILE"
