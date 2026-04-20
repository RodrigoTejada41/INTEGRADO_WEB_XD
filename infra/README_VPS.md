# Deploy em VPS (Producao)

Este projeto esta preparado para deploy em VPS Linux (Ubuntu) com Docker + Docker Compose.

## Estrutura criada

- `docker-compose.prod.yml`
- `infra/nginx/default.conf`
- `infra/env/.env.prod.example`
- `infra/scripts/setup-vps.sh`
- `infra/scripts/deploy-prod.sh`
- `infra/scripts/update.sh`
- `infra/scripts/backup-db.sh`
- `infra/scripts/restore-db.sh`
- `infra/scripts/backup-rotate.sh`
- `infra/scripts/test-restore.sh`
- `infra/scripts/install-backup-cron.sh`
- `infra/scripts/monitor-health.sh`
- `infra/scripts/install-monitoring-cron.sh`
- `infra/scripts/harden-vps.sh`
- `infra/scripts/setup-ssh-key-auth.sh`
- `infra/scripts/enable-https.sh`
- `infra/scripts/renew-certificates.sh`
- `infra/scripts/install-https-cron.sh`
- `.github/workflows/deploy-prod.yml`

## Arquitetura de producao

- `nginx`: unica porta publica (`80/443`)
- `frontend`: painel `sync-admin`, sem exposicao direta externa
- `backend`: API FastAPI interna, acessada via Nginx em `/api/`
- `db`: PostgreSQL interno com volume persistente

Regras aplicadas:
- backend nao exposto publicamente
- banco nao exposto publicamente
- rede interna para containers
- reinicio automatico (`restart: unless-stopped`)
- retencao de 14 meses configuravel por variavel
- challenge ACME habilitado no Nginx para Let's Encrypt

## Primeira instalacao na VPS

1. Clone o repositorio:
```bash
git clone https://github.com/<org-ou-user>/INTEGRADO_WEB_XD.git /opt/integrado_web_xd
cd /opt/integrado_web_xd
```

2. Torne os scripts executaveis:
```bash
chmod +x infra/scripts/*.sh
```

3. Configure ambiente:
```bash
cp infra/env/.env.prod.example .env.prod
nano .env.prod
```

4. Rode setup inicial:
```bash
APP_DIR=/opt/integrado_web_xd BRANCH=main bash infra/scripts/setup-vps.sh
```

5. Suba producao:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/deploy-prod.sh
```

6. Instale monitoramento e backup automatico:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/install-monitoring-cron.sh
APP_DIR=/opt/integrado_web_xd bash infra/scripts/install-backup-cron.sh
```

7. Aplique hardening de seguranca:
```bash
bash infra/scripts/harden-vps.sh
```

Opcional para endurecer SSH apos configurar chave:
```bash
ROOT_LOGIN_MODE=prohibit-password DISABLE_SSH_PASSWORD=true bash infra/scripts/harden-vps.sh
```

## Atualizacoes de deploy

```bash
APP_DIR=/opt/integrado_web_xd BRANCH=main bash infra/scripts/update.sh
```

## Backup e restore do banco

Backup:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/backup-db.sh
```

Backup com rotacao:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/backup-rotate.sh
```

Restore:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/restore-db.sh /opt/integrado_web_xd/infra/backups/postgres_YYYYMMDD_HHMMSS.sql.gz
```

Teste automatico de restore:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/test-restore.sh
```

## HTTPS com Let's Encrypt

Defina no `.env.prod`:
- `DOMAIN=seu-dominio.com`
- `LETSENCRYPT_EMAIL=voce@seu-dominio.com`
- `ENABLE_WWW_DOMAIN=false` (true se voce tambem tiver DNS para `www`)

Emissao inicial:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/enable-https.sh
```

Renovacao manual:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/renew-certificates.sh
```

Renovacao automatica recomendada (cron):
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/install-https-cron.sh
```

## Monitoramento e alertas

`monitor-health.sh` valida:
- uptime do Nginx (`/healthz`)
- health da API (`/api/health`)
- containers com status `exited`
- uso de disco e memoria

Alerta webhook opcional:
- `ALERT_WEBHOOK_URL` no `.env.prod`

## GitHub Actions deploy automatico

Workflow: `.github/workflows/deploy-prod.yml`

Disparo:
- push em `main`
- execucao manual (`workflow_dispatch`)

Secrets necessarios:
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT` (opcional; default 22)
- `VPS_PASSWORD` (fallback, opcional se usar chave)
- `DOMAIN` (opcional, para HTTPS automatico)
- `LETSENCRYPT_EMAIL` (opcional, para HTTPS automatico)

## Dominio e HTTPS (preparado)

- Apontar DNS do dominio para a VPS
- Configurar `DOMAIN` e `LETSENCRYPT_EMAIL` no `.env.prod` (ou nos GitHub Secrets)
- Rodar `infra/scripts/enable-https.sh`
