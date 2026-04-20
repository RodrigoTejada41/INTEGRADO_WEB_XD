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

## Atualizacoes de deploy

```bash
APP_DIR=/opt/integrado_web_xd BRANCH=main bash infra/scripts/update.sh
```

## Backup e restore do banco

Backup:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/backup-db.sh
```

Restore:
```bash
APP_DIR=/opt/integrado_web_xd bash infra/scripts/restore-db.sh /opt/integrado_web_xd/infra/backups/postgres_YYYYMMDD_HHMMSS.sql.gz
```

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

## Dominio e HTTPS (preparado)

- Ajustar `server_name` em `infra/nginx/default.conf`
- Apontar DNS para a VPS
- Provisionar certificados LetsEncrypt e montar em `infra/nginx/certs`
- Habilitar bloco HTTPS comentado no arquivo de Nginx
