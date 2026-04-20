#!/usr/bin/env bash
set -euo pipefail

TARGET_USER="${TARGET_USER:-root}"
PUBLIC_KEY="${PUBLIC_KEY:-}"
DISABLE_PASSWORD_AFTER_KEY="${DISABLE_PASSWORD_AFTER_KEY:-false}"
SSHD_CONFIG="/etc/ssh/sshd_config"

if [ -z "$PUBLIC_KEY" ]; then
  echo "[ssh] PUBLIC_KEY is required"
  exit 1
fi

HOME_DIR="$(eval echo "~$TARGET_USER")"
SSH_DIR="$HOME_DIR/.ssh"
AUTH_FILE="$SSH_DIR/authorized_keys"

mkdir -p "$SSH_DIR"
touch "$AUTH_FILE"
chmod 700 "$SSH_DIR"
chmod 600 "$AUTH_FILE"
chown -R "$TARGET_USER":"$TARGET_USER" "$SSH_DIR"

if ! grep -Fq "$PUBLIC_KEY" "$AUTH_FILE"; then
  echo "$PUBLIC_KEY" >> "$AUTH_FILE"
fi

if [ "$DISABLE_PASSWORD_AFTER_KEY" = "true" ]; then
  if grep -q '^#\?PasswordAuthentication' "$SSHD_CONFIG"; then
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
  else
    echo 'PasswordAuthentication no' >> "$SSHD_CONFIG"
  fi
fi

systemctl restart ssh
echo "[ssh] Key configured for $TARGET_USER"
