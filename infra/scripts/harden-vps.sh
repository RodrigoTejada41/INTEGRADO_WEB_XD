#!/usr/bin/env bash
set -euo pipefail

SSHD_CONFIG="/etc/ssh/sshd_config"
DISABLE_SSH_PASSWORD="${DISABLE_SSH_PASSWORD:-false}"
ROOT_LOGIN_MODE="${ROOT_LOGIN_MODE:-yes}"

echo "[hardening] Installing security packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ufw fail2ban unattended-upgrades

echo "[hardening] Configuring unattended security upgrades"
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

echo "[hardening] Configuring firewall"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "[hardening] Configuring SSH baseline"
if grep -q '^#\?PermitRootLogin' "$SSHD_CONFIG"; then
  sed -i "s/^#\?PermitRootLogin.*/PermitRootLogin $ROOT_LOGIN_MODE/" "$SSHD_CONFIG"
else
  echo "PermitRootLogin $ROOT_LOGIN_MODE" >> "$SSHD_CONFIG"
fi

if grep -q '^#\?X11Forwarding' "$SSHD_CONFIG"; then
  sed -i 's/^#\?X11Forwarding.*/X11Forwarding no/' "$SSHD_CONFIG"
else
  echo 'X11Forwarding no' >> "$SSHD_CONFIG"
fi

if [ "$DISABLE_SSH_PASSWORD" = "true" ]; then
  echo "[hardening] Disabling SSH password authentication"
  if grep -q '^#\?PasswordAuthentication' "$SSHD_CONFIG"; then
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
  else
    echo 'PasswordAuthentication no' >> "$SSHD_CONFIG"
  fi
fi

systemctl restart ssh
systemctl enable fail2ban
systemctl restart fail2ban

echo "[hardening] Security baseline applied"
