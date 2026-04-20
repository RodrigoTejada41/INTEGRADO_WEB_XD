#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/integrado_web_xd}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
LOG_DIR="${LOG_DIR:-$APP_DIR/infra/logs}"
MONITOR_LOG="$LOG_DIR/monitor.log"

mkdir -p "$LOG_DIR"
cd "$APP_DIR"

if [ -f "$ENV_FILE" ]; then
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
  ALERT_WEBHOOK_URL="$(read_env ALERT_WEBHOOK_URL)"
  DISK_ALERT_PERCENT="$(read_env DISK_ALERT_PERCENT 85)"
  MEM_ALERT_PERCENT="$(read_env MEM_ALERT_PERCENT 90)"
else
  ALERT_WEBHOOK_URL=""
  DISK_ALERT_PERCENT=85
  MEM_ALERT_PERCENT=90
fi

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

notify() {
  local message="$1"
  echo "$(timestamp) $message" | tee -a "$MONITOR_LOG"
  if [ -n "$ALERT_WEBHOOK_URL" ]; then
    curl -fsS -X POST "$ALERT_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"$message\"}" >/dev/null || true
  fi
}

if ! curl -fsS http://127.0.0.1/healthz >/dev/null; then
  notify "[ALERT] nginx healthz failed on $(hostname)"
fi

if ! curl -fsS http://127.0.0.1/api/health >/dev/null; then
  notify "[ALERT] backend api health failed on $(hostname)"
fi

if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps --services --filter status=exited | grep -q .; then
  failed_services="$(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps --services --filter status=exited | tr '\n' ',' | sed 's/,$//')"
  notify "[ALERT] exited containers detected: $failed_services"
fi

disk_percent="$(df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
if [ "$disk_percent" -ge "$DISK_ALERT_PERCENT" ]; then
  notify "[ALERT] disk usage high: ${disk_percent}%"
fi

mem_percent="$(free | awk '/Mem:/ {printf "%.0f", ($3/$2)*100}')"
if [ "$mem_percent" -ge "$MEM_ALERT_PERCENT" ]; then
  notify "[ALERT] memory usage high: ${mem_percent}%"
fi

echo "$(timestamp) monitor check ok" >> "$MONITOR_LOG"
