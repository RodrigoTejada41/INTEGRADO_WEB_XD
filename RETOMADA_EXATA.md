# RETOMADA EXATA - INTEGRADO_WEB_XD

Data de atualizacao: 2026-04-27

## Objetivo desta nota
Este arquivo e o ponto de entrada para retomar o projeto sem redescobrir contexto.

## Estado atual (validado)
- Checkpoint mais recente: hotfix de rotas do painel admin e schema de relatorios em producao.
- Branch local atual: `codex/fix-connected-apis-nginx`.
- Commit local anterior nesta branch: `2a41261` - `fix: route connected apis through nginx`.
- Existem mudancas locais staged ainda sem commit porque a sessao foi interrompida antes do commit final.
- Arquivos staged neste checkpoint:
  - `backend/models/venda.py`
  - `backend/repositories/venda_repository.py`
  - `backend/schemas/sync.py`
  - `backend/sql/postgresql_schema.sql`
  - `infra/nginx/default.conf`
  - `tests/test_production_operations.py`
  - `tests/test_sync_upsert.py`
- VPS ativa em `172.238.213.72` com stack em `/opt/integrado_web_xd`.
- Deploy de producao com `docker-compose.prod.yml`.
- Containers esperados:
  - `integrado_nginx`
  - `integrado_backend`
  - `integrado_frontend`
  - `integrado_db`
- Dominio principal ativo:
  - `https://movisystecnologia.com.br/` redireciona para `/MoviRelatorios/`
  - Cliente em `https://movisystecnologia.com.br/MoviRelatorios`
  - API/Docs em `https://movisystecnologia.com.br/admin`
- SSL ativo (Let's Encrypt) com renovacao automatizada ja preparada.

## Checkpoint operacional mais recente - 2026-04-27

### Problema reportado
- Tela `APIs Conectadas` retornava `404 Not Found` pelo Nginx.
- Tela `Relatorios` tambem retornava `404 Not Found`.
- Apos corrigir o roteamento, a tela `Relatorios` autenticada retornou `500 Internal Server Error`.

### Causas confirmadas
- O `sync-admin` usa links absolutos como `/connected-apis`, `/reports` e `/client/reports`.
- A aplicacao esta publicada sob `/admin`, mas o Nginx so tinha compatibilidade para alguns caminhos absolutos (`/dashboard`, `/settings`, etc.).
- O 500 de relatorios vinha do backend central:
  - endpoint: `GET /admin/tenants/12345678000199/reports/overview`
  - erro: `column vendas.branch_code does not exist`
- O codigo de relatorios esperava `branch_code` e `terminal_code`, mas o schema real do PostgreSQL ainda nao tinha essas colunas.

### Correcao aplicada diretamente na VPS
- `infra/nginx/default.conf` copiado para `/opt/integrado_web_xd/infra/nginx/default.conf`.
- Nginx validado e recarregado:
  - `nginx -t` OK
  - `nginx -s reload` OK
- Migração SQL segura aplicada no PostgreSQL de producao:
  - `ALTER TABLE vendas ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);`
  - `ALTER TABLE vendas ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);`
  - `ALTER TABLE vendas_historico ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);`
  - `ALTER TABLE vendas_historico ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);`
  - `CREATE INDEX IF NOT EXISTS ix_vendas_empresa_branch ON vendas (empresa_id, branch_code);`
  - `CREATE INDEX IF NOT EXISTS ix_vendas_empresa_terminal ON vendas (empresa_id, terminal_code);`

### Validacao em producao executada
- Login admin:
  - usuario: `admin`
  - senha operacional temporaria usada nesta sessao: `MoviSys@2026#Admin`
  - `POST /admin/login` -> `302`
- `GET https://movisystecnologia.com.br/connected-apis` autenticado -> `200`
- `GET https://movisystecnologia.com.br/admin/connected-apis` autenticado -> `200`
- `GET https://movisystecnologia.com.br/reports` autenticado -> `200`
- `GET https://movisystecnologia.com.br/admin/reports` autenticado -> `200`

### Correcao registrada no codigo local
- Nginx:
  - adicionadas rotas compativeis para `/connected-apis`, `/reports` e `/client/reports`.
- Backend:
  - `Venda` e `VendaHistorico` agora incluem `branch_code` e `terminal_code`.
  - `VendaPayload` agora aceita `branch_code` e `terminal_code`.
  - `VendaRepository.bulk_upsert` persiste e atualiza esses campos.
  - `retain_recent_data` arquiva esses campos em `vendas_historico`.
  - `backend/sql/postgresql_schema.sql` inclui colunas, alter idempotente e indices.
- Testes:
  - contrato Nginx cobre `/connected-apis`, `/reports` e `/client/reports`.
  - upsert cobre persistencia e update de `branch_code`/`terminal_code`.

### Validacao local executada
- `py -3 -m pytest tests/test_production_operations.py -q` -> `8 passed`.
- `py -3 -m pytest tests/test_sync_upsert.py tests/test_production_operations.py -q` -> `11 passed`.
- `py -3 -m pytest -q` -> `26 passed, 1 skipped`.

### Estado Git exato ao pausar
- Branch: `codex/fix-connected-apis-nginx`.
- Worktree com arquivos staged e sem commit final.
- Commit que ainda precisa ser criado:
  - sugestao: `fix: restore reports route and sales branch schema`
- Depois do commit:
  - `git push -u origin codex/fix-connected-apis-nginx`
  - abrir/atualizar PR: `https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD/pull/new/codex/fix-connected-apis-nginx`
- Observacao: `main` esta protegida; nao usar push direto para `main`.

## Correcao mais recente aplicada
- Problema reportado: `https://movisystecnologia.com.br/admin/docs` mostrava `Failed to load API definition`.
- Causa: Swagger em `/admin/docs` solicitava `'/openapi.json'` na raiz e o Nginx nao roteava essa URL para o backend.
- Correcao: adicionadas rotas dedicadas no Nginx:
  - `location = /openapi.json`
  - `location = /docs/oauth2-redirect`
- Arquivo alterado:
  - `infra/nginx/default.conf`
- Commit local desta correcao:
  - `34d467f` - `fix(nginx): expose openapi route for swagger under /admin/docs`

## Validacoes de runtime executadas
- `/admin/docs` -> `200 OK`
- `/openapi.json` -> `200 OK`
- Containers backend/frontend/db em estado `healthy`
- Nginx ativo com portas `80/443` publicadas

## Teste real de comunicacao local -> web (2026-04-22)
- Fluxo validado conforme arquitetura:
  - Cliente local (simulado com `agent_local` contract) enviando para `POST /sync`
  - Entrada publica usada: `https://movisystecnologia.com.br/admin/api/sync`
  - Headers: `X-Empresa-Id` + `X-API-Key`
- Resultado de integracao:
  - 1a chamada: `inserted_count=1`, `updated_count=0`
  - 2a chamada (mesmo `uuid`): `inserted_count=0`, `updated_count=1`
  - Banco central confirmou UPSERT com valor final atualizado.
- Validacao de seguranca:
  - Chave invalida retorna `401` com `Credenciais invalidas.`

## Teste real multi-tenant (segundo cliente) - 2026-04-22
- Tenant de teste adicional provisionado: `99887766000155` (Cliente Teste B).
- Insert real executado em `POST https://movisystecnologia.com.br/admin/api/sync` com API key propria.
- Resultado: `200` com `inserted_count=1`.
- Isolamento validado no banco central:
  - registro presente em `empresa_id=99887766000155`
  - `count=0` para o mesmo `uuid` em `empresa_id=12345678000199`

## Painel real de administracao de APIs (2026-04-22)
- Backend admin expandido com gestao real de tenants/API:
  - `GET /admin/tenants` (listagem)
  - `DELETE /admin/tenants/{empresa_id}` (desativacao)
- Painel `settings` atualizado com tabela operacional:
  - lista de clientes (empresa_id, nome, status)
  - acao de rotacionar chave por cliente
  - acao de desativar API por cliente
- Validacao executada em producao:
  - tenant temporario criado, listado como ativo, desativado e listado como inativo.

## Vinculacao por codigo (device code) - implementado no repo (2026-04-22)
- Objetivo: instalar API local no cliente sem expor IP, SSH, usuario ou senha.
- Fluxo novo:
  - Admin gera codigo temporario no painel (`/settings`) por `empresa_id`.
  - Cliente local informa apenas o codigo no agente.
  - Backend valida o codigo (uso unico + expiracao) e devolve API key de agente.
  - Agente salva chave localmente e passa a sincronizar em `POST /sync`.
- Endpoints novos:
  - `POST /admin/tenants/{empresa_id}/pairing-codes` (admin)
  - `POST /agent/pairings/activate` (publico com codigo)
- Seguranca:
  - codigo em hash no banco, expira (TTL), nao reutilizavel.
  - chave gerada vinculada ao `empresa_id` correto, mantendo isolamento multi-tenant.
- Tela local para tecnico (nova):
  - `python -m agent_local.pairing_ui`
  - atalho PowerShell: `scripts/open-agent-pairing-ui.ps1`
  - finalidade: duas abas para operacao de campo:
    - `Vinculacao por Codigo` (onboarding sem editar `.env`)
    - `Configuracao Manual` (troca de URL do servidor/VPS + chave manual)
  - protecao solicitada:
    - alteracao manual de servidor/chave exige senha local
    - senha agora prioriza Windows Credential Manager:
      - target: `MoviSync.ManualConfig.Password`
      - script de cadastro: `scripts/set-agent-manual-password.ps1`
    - fallback opcional por `.env`: `AGENT_MANUAL_CONFIG_PASSWORD`

## Risco importante observado
- Durante ajuste manual houve loop de restart do Nginx por BOM no arquivo de config (`unknown directive "﻿upstream"`).
- Mitigacao aplicada: arquivo salvo sem BOM e Nginx reiniciado com sucesso.
- Regra daqui para frente: evitar edicao de `infra/nginx/default.conf` com BOM.

## Como retomar em 2 minutos
1. Entrar na VPS por chave:
   - script local: `infra/scripts/ssh-prod.ps1`
2. Confirmar stack:
   - `docker ps`
3. Validar rotas principais:
   - `curl -I https://movisystecnologia.com.br/admin/docs`
   - `curl -I https://movisystecnologia.com.br/openapi.json`
   - `curl -I https://movisystecnologia.com.br/MoviRelatorios/`
4. Se houver mudancas pendentes no repo, subir deploy:
   - `infra/scripts/deploy-prod.sh` (na VPS)

## Proximos passos recomendados (curto prazo)
1. Fazer push do commit `34d467f` e merge em `main` para manter convergencia repo <-> VPS.
2. Executar deploy via GitHub Actions em `main` e validar rotas publicas novamente.
3. Opcional tecnico: migrar docs da API para `docs_url='/admin/docs'` + `root_path='/admin'` no FastAPI para eliminar dependencia do alias `/openapi.json`.

## Checkpoint de convergencia backend/VPS - 2026-04-27
- Problema confirmado:
  - a VPS tinha funcionalidades avancadas em arquivos locais/dirty que nao estavam no `main` oficial;
  - ao alinhar a VPS com `origin/main`, houve downgrade funcional do backend;
  - sintomas em producao: `/reports` autenticado retornava `500` por endpoints backend ausentes (`/admin/tenants/{empresa_id}/reports/overview`, `/api/v1/clients`, `/api/v1/clients/summary`).
- Correcao aplicada em branch isolada:
  - branch local: `codex/restore-backend-reporting-contract`;
  - restaurado o contrato backend avancado a partir de `origin/codex/vps-https-deploy-contract`;
  - incluidos endpoints de relatorios por tenant, APIs remotas conectadas, pareamento por codigo, health/readiness avancado, auditoria com `correlation_id`, metricas HTTP e fila/scheduler avancados;
  - corrigido o wiring do `tenant_pairing_router` no FastAPI;
  - ajustada politica de retry do worker para nao enviar falhas permanentes para DLQ na primeira tentativa.
- Validacao local:
  - `py -3 -m pytest tests/test_production_operations.py tests/test_sync_upsert.py tests/test_api_integration.py -q` -> `13 passed`;
  - `py -3 -m pytest tests/test_tenant_scheduler.py -q` -> `3 passed`;
  - `py -3 -m pytest -q` -> `26 passed, 1 skipped`.
- Estado Git esperado:
  - commit pendente na branch `codex/restore-backend-reporting-contract`;
  - depois do commit: push, PR para `main`, merge aprovado e deploy na VPS.
- Regra operacional:
  - nao alinhar VPS com `main` sem validar antes se as funcionalidades existentes em producao estao versionadas;
  - qualquer hotfix manual em VPS deve virar commit/PR antes de novo reset/redeploy.

## Evolucao de relatorios cliente/admin - 2026-04-27
- Decisao de produto:
  - relatorios saem da navegacao principal do admin;
  - admin mantem `/reports` apenas como tela tecnica de teste/validacao;
  - uso operacional principal fica no portal cliente em `/client/reports`.
- Backend:
  - venda canonica agora aceita dimensoes opcionais:
    - `tipo_venda`
    - `forma_pagamento`
    - `familia_produto`
  - adicionada migracao `v005_sales_report_dimensions`;
  - relatorios ganharam filtro por horario (`start_time`, `end_time`) usando `data_atualizacao`;
  - novo endpoint: `/admin/tenants/{empresa_id}/reports/breakdown` com `group_by` em `tipo_venda`, `forma_pagamento` ou `familia_produto`.
- Painel:
  - filtros adicionados:
    - vendas do dia
    - mensal
    - trimestral
    - semestral
    - anual
    - datas X a Y
    - horario X a Y
  - graficos separados:
    - serie diaria
    - top produtos
    - tipo de venda
    - forma de pagamento
    - familia de produto
- Validacao:
  - `py -3 -m pytest -q` -> `27 passed, 1 skipped`.
- Deploy final:
  - branch em producao: `codex/restore-backend-reporting-contract`;
  - commit em producao: `fd8fb8b`;
  - migracao aplicada na VPS: `current_version=5`;
  - containers saudaveis: `integrado-backend`, `integrado-frontend`, `integrado-nginx`, `integrado-db`;
  - smoke autenticado na VPS:
    - `health=200`
    - `ready=200`
    - `login=302`
    - `reports=200`
    - `connected_apis=200`
- Pendente critico:
  - abrir/mergear PR da branch `codex/restore-backend-reporting-contract` em `main`;
  - nao fazer deploy automatico de `main` antes do merge, para nao perder a evolucao dos relatorios.
