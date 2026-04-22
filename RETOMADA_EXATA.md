# Retomada Exata

Ultimo checkpoint: 2026-04-21 00:00:00 -03:00
Branch atual: `main`
Workspace local: alterado e com novos artefatos de producao VPS

## 1) Onde voce parou
- Fase de backlog concluida ate `P18`.
- Ultima entrega funcional: observabilidade avancada por tenant + correlacao ponta a ponta de logs (`correlation_id`) + endpoint admin de observabilidade.
- Etapa extra iniciada e concluida no codigo: estrutura completa para deploy em VPS Linux com Docker/Nginx/GitHub Actions.
- Ultima validacao executada: `py -3 -m pytest -q` com `28 passed`.
- Validacao operacional local executada nesta sessao: `.env.prod` local criado, migração aplicada via `scripts/db_migrate.py`, stack produtivo subiu com `db`, `backend`, `frontend` e `nginx` saudaveis, e edge validado em `http://127.0.0.1:8088` por conflito na porta `80` do host.

## 2) O que foi concluido
- `P1-P5`: scheduler por tenant, fila persistida, DLQ, criptografia base, RBAC e auditoria.
- `P6-P9`: observabilidade HTTP, hardening base, scripts de carga, pipeline com migracao/rollback.
- `P10-P14`: escopo multiempresa por empresa/filial/terminal, exportacao Excel/PDF, melhorias de painel, snapshot local-first, tuning de escala.
- `P15`: migracoes reais de schema com versionamento e rollback por versao/passos.
- `P16`: health/readiness de producao no backend e no `sync-admin`.
- `P17`: backpressure por tenant + fairness de selecao + retry policy por classe de falha (permanent/auth/transient).
- `P18`: observabilidade por tenant no backend e no painel + correlacao de logs.
- Etapa extra VPS: `docker-compose.prod.yml`, Nginx reverso, scripts de setup/deploy/update/backup/restore e workflow GitHub Actions por SSH.

## 3) Arquivos chave alterados na ultima fase
- Backend
- `backend/utils/correlation.py`
- `backend/utils/metrics.py`
- `backend/config/logging.py`
- `backend/main.py`
- `backend/api/routes/sync.py`
- `backend/api/routes/tenant_admin.py`
- `backend/services/tenant_sync_worker.py`
- `backend/services/tenant_sync_scheduler.py`
- `backend/schemas/tenant_observability.py`
- `backend/Dockerfile`

- Sync admin
- `sync-admin/app/services/control_service.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/dashboard.html`

- Infra VPS / CI-CD
- `docker-compose.prod.yml`
- `.env.prod.example`
- `infra/nginx/default.conf`
- `infra/nginx/ssl-example.conf`
- `infra/scripts/setup-vps.sh`
- `infra/scripts/deploy-prod.sh`
- `infra/scripts/update.sh`
- `infra/scripts/backup-db.sh`
- `infra/scripts/restore-db.sh`
- `.github/workflows/deploy-prod.yml`
- `infra/VPS_DEPLOY.md`

- Testes atualizados
- `tests/test_observability.py`
- `tests/test_backend_audit.py`

## 4) Como retomar exatamente
1. Abrir a base local-first:
```powershell
Get-Content .\CEREBRO_VIVO.md
Get-Content .\.cerebro-vivo\README.md
```
2. Revalidar baseline tecnico:
```powershell
py -3 -m pytest -q
```
3. Confirmar status de alteracoes locais:
```powershell
git status --short
```
4. Se o objetivo for deploy: abrir guia `infra/VPS_DEPLOY.md`.
5. Na VPS, executar:
```bash
bash infra/scripts/setup-vps.sh
cp .env.prod.example .env.prod
bash infra/scripts/deploy-prod.sh
```
6. Configurar GitHub Secrets para deploy automatico:
`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT` (opcional), `VPS_APP_DIR` (opcional).

## 5) Proximas prioridades abertas
- `P19`: governanca e seguranca (rotacao/expiracao de segredos e auditoria expandida).
- `P20`: refinamentos finais de produto e operacao.
- Etapa operacional pendente: executar deploy real na VPS e validar health via Nginx.
- Etapa local concluida nesta sessao: repetir validacao do stack local apos qualquer nova mudanca em `docker-compose.prod.yml`, `infra/nginx/default.conf` ou `.env.prod`.
- Sessao pausada apos registrar o checkpoint; continuar daqui exige reabrir este arquivo e a memoria executiva antes de qualquer nova decisao.

## 6) Regras para continuidade sem regressao
- Nao remover isolamento por `empresa_id`.
- Nao quebrar retention de `14` meses.
- Nao acessar banco direto na camada de API.
- Nao reduzir cobertura dos testes existentes.
- Antes de encerrar qualquer ciclo: rodar `py -3 -m pytest -q`.
- Nao registrar credenciais sensiveis em arquivo de repositorio.
- Esta deve ser a referencia principal de retomada quando a conversa for reaberta.
