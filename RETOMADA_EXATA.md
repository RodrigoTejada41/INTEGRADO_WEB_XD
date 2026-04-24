# Retomada Exata

Ultimo checkpoint: 2026-04-24 -03:00
Branch atual: `main`
Workspace local: alterado com memoria executiva atualizada e docs de continuidade reconciliados

## 1) Onde voce parou
- Fase de backlog concluida ate `P20`.
- Ultima entrega funcional consolidada: observabilidade avancada por tenant + correlacao ponta a ponta de logs (`correlation_id`) + endpoint admin de observabilidade.
- Etapa extra de producao concluida: stack VPS com Docker, Nginx, scripts e GitHub Actions.
- Ultima validacao tecnica executada: `py -3 -m pytest -q` com `86 passed, 1 skipped`.
- Novo contrato adicionando simulacao local/VPS em um unico teste end-to-end, cobrindo provisionamento via painel, registro do cliente local, rotacao de chave e validacao do bloqueio da credencial antiga.
- O mesmo contrato agora cobre tambem o ciclo bidirecional de `force_sync`, com enfileiramento pelo painel, pull de comandos e resultado aplicado pelo cliente local.
- Smoke de release documentado e executavel via `RELEASE_SMOKE_BASE_URL` para validar a VPS publicada apos cada deploy.
- O dashboard operacional do `sync-admin` agora mostra o ciclo de sincronizacao por fonte, com `last_scheduled_at`, `next_run_at` e fallback rapido quando a API de controle esta offline.
- Deploy VPS concluido em `https://movisystecnologia.com.br`.
- `GET /admin/api/health/ready` responde `200`.
- `GET /MoviRelatorios/` responde `302`.
- `integrado_backend`, `integrado_frontend`, `integrado_db` e `integrado_nginx` estao saudaveis.
- Divergencia antiga entre `P18` e `P20` foi resolvida em favor de `P20` como linha canonica atual.

## 2) O que foi concluido
- `P1-P5`: scheduler por tenant, fila persistida, DLQ, criptografia base, RBAC e auditoria.
- `P6-P9`: observabilidade HTTP, hardening base, scripts de carga, pipeline com migracao/rollback.
- `P10-P14`: escopo multiempresa por empresa/filial/terminal, exportacao Excel/PDF, melhorias de painel, snapshot local-first, tuning de escala.
- `P15`: migracoes reais de schema com versionamento e rollback por versao/passos.
- `P16`: health/readiness de producao no backend e no `sync-admin`.
- `P17`: backpressure por tenant + fairness de selecao + retry policy por classe de falha.
- `P18`: observabilidade por tenant no backend e no painel + correlacao de logs.
- `P19`: governanca de segredos e auditoria expandida.
- `P20`: endurecimento operacional de deploy, readiness e validacao de producao.
- Etapa extra VPS: `docker-compose.prod.yml`, Nginx reverso, scripts de setup/deploy/update/backup/restore e workflow GitHub Actions por SSH.
- Estado atual da VPS: commit `5a06f1d`, com producao estavel e contrato de borda validado.

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
- `infra/SSH_ACESSO.md`

- Testes atualizados
- `tests/test_observability.py`
- `tests/test_backend_audit.py`
- `tests/test_production_operations.py`
- `tests/test_local_vps_dual_simulation.py`

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
4. Se o objetivo for deploy, abrir `infra/VPS_DEPLOY.md`.
5. Na VPS, executar:
```bash
bash infra/scripts/setup-vps.sh
cp .env.prod.example .env.prod
bash infra/scripts/deploy-prod.sh
```
6. Configurar GitHub Secrets para deploy automatico:
`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT` (opcional), `VPS_APP_DIR` (opcional).

## 5) Proximas prioridades abertas
- Reboot local para liberar o lock do `C:\MoviSyncAgent` e retomar `3) Atualizar` do cliente MoviSync, se esse fluxo ainda for necessario.
- A frente de produto ganhou acoes manuais de `Sincronizar agora` e `Sincronizar todas as fontes` no cockpit de fontes do `sync-admin`, com contrato de API e UI cobertos por teste e feedback visual de flash em sucesso/erro.

## 6) Regras para continuidade sem regressao
- Nao remover isolamento por `empresa_id`.
- Nao quebrar retention de `14` meses.
- Nao acessar banco direto na camada de API.
- Nao reduzir cobertura dos testes existentes.
- Antes de encerrar qualquer ciclo: rodar `py -3 -m pytest -q`.
- Nao registrar credenciais sensiveis em arquivo de repositorio.
- Esta deve ser a referencia principal de retomada quando a conversa for reaberta.

## 7) Atualizacao desta pausa

- Validacao final desta retomada: `py -3 -m pytest -q` com `60 passed`.
- O temp root do pytest foi movido para `runtime/pytest-tmp` dentro do workspace para eliminar a dependencia da home do usuario e estabilizar `tmp_path`.
- Validacao final desta retomada: `py -3 -m pytest -q` com `62 passed`.
- Ajuste aplicado antes da pausa: `infra/nginx/default.conf` alinhado com `backend_upstream` e `frontend_upstream` para fechar o contrato de readiness.
- O backend agora usa `ENVIRONMENT=development` como default e ativa `https_only` no `SessionMiddleware` apenas em producao.
- Validacao final desta retomada: `py -3 -m pytest -q` com `67 passed`.
- Ajuste de borda desta sessao: `infra/nginx/default.conf` trata `location /admin/api/` separadamente de `location /admin/`, porque o cliente local registra em `/admin/api/api/v1/register`.
- Validacao local desta correcao: `py -3 -m pytest tests/test_production_operations.py -q` com `5 passed`, seguido de `py -3 -m pytest -q` com `60 passed`.
- Ajuste de isolamento de teste desta sessao: `conftest.py` passou a restaurar `os.environ` apos cada teste para impedir vazamento de ambiente entre casos.
- Validacao final desta sessao: `py -3 -m pytest -q` com `67 passed`.
- Entrega de produto desta sessao: o cockpit de fontes do `sync-admin` ganhou as acoes manuais `Sincronizar agora` e `Sincronizar todas as fontes`, com contrato de backend e web cobertos por teste e feedback visual de flash no `base.html`.
- Validacao final desta sessao: `py -3 -m pytest -q` com `88 passed, 1 skipped`.
- Deploy VPS concluido em `https://movisystecnologia.com.br` com `GET /admin/api/health/ready` em `200`, `GET /MoviRelatorios/` em `302` e containers `backend`, `frontend`, `db` e `nginx` saudaveis.
- Runbook operacional consolidado em `infra/RUNBOOK_PRODUCAO.md`, cobrindo deploy manual, update, backup, restore, rollback e health checks.
- Controle remoto local do `sync-admin` passou a ter cobertura de allowlist por IP no token local.
- O compose de producao passou a ter contrato explicito de exposicao publica apenas para o `nginx`.
- O `remote_agent` do `sync-admin` passou a ter contrato de ciclo desabilitado por `remote_command_pull_enabled` e snapshot de status com estado de comandos.
- A fumaça de readiness agora valida backend, sync-admin e snapshot do `remote_agent` em um unico contrato.
- Checkpoint atual consolidado no commit `46f6b78`, com suite completa em `84 passed` e worktree limpo.
- O comando remoto `force_sync` agora tem cobertura funcional de efeito real, com estado local e log operacional validados.
- O contrato E2E da API central agora cobre provisionamento, registro, sync, revogacao por rotacao de chave e bloqueio da chave antiga.
- O contrato E2E da API central agora tambem valida rastreio por `correlation_id` em auditoria e log de cliente.
- A revogacao web do `sync-admin` em `/settings/rotate-tenant-key` agora tem cobertura dedicada, com redirecionamento, flash e aplicacao da chave no arquivo do agente.
- O contrato de migrations agora valida `target_version` e contagem da tabela `sync_schema_migrations`, reduzindo o drift entre baseline local e rollback.
- O projeto ganhou um teste local que simula simultaneamente o painel local e a API central/VPS, sem depender de rede externa.
- O deploy agora tem um smoke de release que valida `healthz`, `readyz/backend`, `readyz/sync-admin`, `admin/api/health/ready`, `admin/` e `MoviRelatorios/`.
- O cockpit de fontes agora consolida status vivo por fonte, ultima acao, ultimo disparo e refresh automatico no dashboard.
- Divergencia antiga entre `P18` e `P20` resolvida: a fonte de verdade atual passa a considerar `P20` concluido.
- Risco atual principal deslocado para o drift local de migracoes e testes, especialmente a divergencia entre baseline local e contrato de rollback/migration.
- Proxima retomada: abrir primeiro `RETOMADA_EXATA.md`, depois `cerebro_vivo/estado_atual.md`, depois `cerebro_vivo/historico_decisoes.md`.

## 8) Retomada rapida

1. Abrir `RETOMADA_EXATA.md`.
2. Verificar `git status --short`.
3. Validar com `py -3 -m pytest -q`.
4. Se for deploy, seguir `infra/RUNBOOK_PRODUCAO.md`.
5. Se for VPS, seguir `infra/VPS_DEPLOY.md`.
