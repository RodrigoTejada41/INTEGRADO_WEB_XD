# RETOMADA EXATA - INTEGRADO_WEB_XD

Data de atualizacao: 2026-04-28

## Checkpoint retomada operacional - reset seguro de vendas - 2026-04-29

### Problema operacional
- A correcao de `familia_produto` ja esta no `main` e em producao.
- Os registros antigos da empresa `12345678000199` continuam sem familia real porque foram sincronizados antes do agente local enviar esse campo.
- O agente local tinha apenas checkpoint JSON, sem comando seguro para reprocessar vendas antigas.

### Correcao aplicada localmente
- `agent_local/sync/checkpoint_store.py` ganhou metodo `reset`.
- Criado CLI:
  - `python -m agent_local.sync.reset_checkpoint`
- Criado CLI de ciclo unico:
  - `python -m agent_local.sync.run_once`
- O comando exige `--confirm` para gravar no checkpoint.
- O reset e por chave isolada:
  - `{empresa_id}:vendas`
- Nao altera API key, configuracao de banco, URL do servidor ou dados sincronizados.
- `agent_local/db/mariadb_client.py` agora trata `AGENT_SOURCE_QUERY` legado de `salesdocumentsreportview` sem campos canonicos como autodeteccao.
- `agent_local/db/xd_sales_mapper.py`:
  - converte `cancelada` para booleano;
  - filtra registros com `TotalAmount <= 0`, porque a API central exige `valor > 0`.
- `agent_local/sync/api_client.py` agora inclui corpo de erro HTTP na excecao para diagnostico de 422/400.
- `infra/client-agent/install-agent-client.ps1` atualiza `AGENT_SOURCE_QUERY` legado para `auto` e grava `.env` sem BOM.

### Comando operacional para reprocessar vendas
- Reprocessar tudo:
  - `py -3 -m agent_local.sync.reset_checkpoint --empresa-id 12345678000199 --checkpoint-file agent_local/data/checkpoints.json --confirm`
- Reprocessar a partir de uma data especifica:
  - `py -3 -m agent_local.sync.reset_checkpoint --empresa-id 12345678000199 --checkpoint-file agent_local/data/checkpoints.json --since 2026-04-01T00:00:00 --confirm`
- Depois do reset:
  - executar o agente local normalmente para reenviar os lotes;
  - como o backend usa UPSERT por `empresa_id + uuid`, o reenvio atualiza os registros existentes sem misturar tenants.

### Validacao local
- `py -3 -m pytest tests\test_agent_checkpoint_reset.py tests\test_agent_local_sales_mapping.py -q` -> `6 passed`.
- CLI validado com arquivo de checkpoint isolado em `output/test_agent_checkpoint_reset/cli_checkpoints.json`.
- Validacao apos hardening de mapper/client:
  - `py -3 -m pytest tests\test_agent_checkpoint_reset.py tests\test_agent_local_sales_mapping.py tests\test_sync_upsert.py -q` -> `12 passed`.

### Execucao real no agente instalado
- Instalacao real detectada:
  - `C:\MoviSyncAgent`
- Corrigido `.env` instalado:
  - `AGENT_SOURCE_QUERY=auto`
  - `.env` regravado sem BOM para `AGENT_EMPRESA_ID` carregar corretamente.
- Checkpoint real resetado:
  - `12345678000199:vendas=1970-01-01T00:00:00+00:00`
- Primeiro lote com `BATCH_SIZE=1`:
  - `updated_count=1`
- Lote 50:
  - `processed_count=50`
- Lotes seguintes executados com sucesso, incluindo lotes de 500 e 1000.
- Erros encontrados e corrigidos:
  - `422 valor > 0` causado por venda local com `TotalAmount=0`;
  - corrigido com filtro de origem `COALESCE(TotalAmount, 0) > 0`.
- Reprocessamento continuado em 2026-04-30 com lotes de ate 1000.
- Checkpoint real final:
  - `2026-03-28T15:36:02+00:00`
- Ultimo ciclo:
  - `processed_count=0`
- Intervalo do agente restaurado:
  - `SYNC_INTERVAL_MINUTES=15`
- Processo em background:
  - nao ha `python.exe` ativo em `C:\MoviSyncAgent` no momento deste registro.
- Validacao na VPS apos catch-up:
  - `total=48895`
  - `family_filled=48894`
  - `family_distinct=13`

### Proximo passo seguro
1. Validar visualmente `/client/reports?report_view=families` em producao.
2. Conferir uma amostra do unico registro ainda sem `familia_produto`.
3. Manter `SYNC_INTERVAL_MINUTES=15` no agente instalado.

## Checkpoint relatorios comerciais/financeiros - 2026-04-29

### Correcao familia em relatorios cliente - 2026-04-29

Problema validado em producao:

- URL afetada:
  - `/client/reports?empresa_id=12345678000199&report_view=families&period_preset=custom&top_limit=10&recent_limit=20`
- Diagnostico no PostgreSQL da VPS:
  - `total_rows=485`;
  - `family_not_null=0`;
  - `family_filled=0`;
  - amostras tambem sem `codigo_produto_local`.
- Causa:
  - dados existentes foram sincronizados sem `familia_produto` e sem `codigo_produto_local`;
  - o mapper XD precisava cobrir tambem o caminho `ItemKeyId -> Items.KeyId -> Items.GroupId -> Itemsgroups`.

Correcao aplicada:

- `agent_local/db/xd_sales_mapper.py` agora busca familia:
  - por `ItemGroupId` direto quando existir;
  - por `Items.GroupId` a partir de `ItemKeyId` quando a view/tabela de vendas nao trouxer `ItemGroupId`.
- `backend/repositories/venda_repository.py` trata familia vazia como `Nao informado` nos agrupamentos.
- Testes adicionados:
  - mapper XD com `Items + Itemsgroups`;
  - agrupamento de familia vazia.

Validacao local:

- `py -3 -m pytest tests\test_agent_local_sales_mapping.py tests\test_sync_upsert.py -q` -> `9 passed`.
- `py -3 -m pytest -q` -> `51 passed, 1 skipped`.

Git/VPS:

- PR:
  - `#25` - `Fix XD product family mapping in reports`.
- Commit em `main`:
  - `b3fb936` - `fix: map XD product families through items (#25)`.
- Deploy VPS:
  - `/opt/integrado_web_xd` em `b3fb936`;
  - `bash infra/scripts/deploy-prod.sh` executado com sucesso;
  - migration sem pendencias: `current_version=6`;
  - containers `integrado-backend`, `integrado-frontend`, `integrado-nginx` healthy.
- Pos-deploy:
  - `infra/nginx/default.conf` foi restaurado para a versao Git e recarregado com `nginx -s reload`;
  - HTTPS validado por GET a partir da VPS:
    - `/healthz` -> `200`;
    - `/readyz/backend` -> `200`;
    - `/readyz/sync-admin` -> `200`;
    - `/admin/api/health/ready` -> `200`.
- API interna validada:
  - `/admin/tenants/12345678000199/reports/breakdown?group_by=familia_produto&limit=10` -> `200`;
  - retorno atual: `Nao informado`, `total_records=485`, `total_sales_value=20132.21`.

Ponto operacional:

- Para a empresa `12345678000199`, a producao so passara a mostrar familias reais depois de atualizar o agente local e reenviar/reprocessar as vendas do periodo, porque os registros atuais no banco central nao possuem a informacao.

### Entrega local
- Modulo de relatorios ampliado para BI comercial/financeiro:
  - filtros por produto, codigo local, familia, forma de pagamento, bandeira, operador, cliente, cancelamento e status;
  - agrupamentos adicionais por pagamento, bandeira, familia, categoria, terminal, filial, operador, cliente, status e codigo local;
  - totais detalhados: bruto, descontos, acrescimos, liquido e quantidade;
  - exportacao CSV/Excel/PDF preservando filtros aplicados;
  - painel com filtros avancados e tabela detalhada;
  - tabela `produto_de_para` por empresa, usando `codigo_produto_local` como referencia principal.
- Migration nova:
  - `backend/db/migrations/v006_sales_report_detail_fields.py`.
- Documentacao nova:
  - `docs/relatorios_comerciais_financeiros.md`.

### Validacao local
- `py -3 -m compileall backend sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_sync_upsert.py tests\test_sync_admin_rbac.py -q` -> `12 passed`.
- `py -3 -m pytest -q` -> `41 passed, 1 skipped`.

### Proximo passo seguro
1. Revisar visualmente `/reports` e `/client/reports`.
2. Aplicar migration v006 no ambiente alvo antes do deploy.
3. Subir branch/PR e validar exportacoes com dados reais do cliente.

## Checkpoint referencia XD Software - 2026-04-29

### Arquivo consultado
- `TABELAS DO BANCO XD/REFERENCIA TABELAS BD XD SOFTWARE.xlsx`

### Entrega local adicional
- `agent_local/db/xd_sales_mapper.py` agora usa a referencia XD para fallback automatico:
  - origem preferencial: `salesdocumentsreportview`;
  - origem alternativa: `Documentsbodys + Documentsheaders`;
  - pagamentos: `Invoicepaymentdetails + Xconfigpaymenttypes`;
  - familia: `Itemsgroups`;
  - codigo local do produto: `ItemKeyId -> codigo_produto_local`.
- Criadas rotas de diagnostico no `sync-admin`:
  - `GET /settings/xd-mapping`;
  - `GET /settings/xd-mapping/routes`.
- O diagnostico mostra tabelas/colunas detectadas e tipo de origem usada sem expor senha.

### Validacao local
- `py -3 -m pytest tests\test_xd_sales_mapper.py tests\test_sync_admin_rbac.py tests\test_sync_upsert.py -q` -> `16 passed`.
- `py -3 -m pytest -q` -> `45 passed, 1 skipped`.

## Checkpoint CRUD DE/PARA Produtos - 2026-04-29

### Entrega local adicional
- CRUD administrativo completo de `produto_de_para`:
  - `GET /admin/tenants/{empresa_id}/produto-de-para`;
  - `POST /admin/tenants/{empresa_id}/produto-de-para`;
  - `PUT /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`;
  - `DELETE /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`;
  - `GET /admin/tenants/{empresa_id}/produto-de-para/unmapped`.
- Tela `/settings` recebeu secao `DE/PARA Produtos`:
  - cadastro manual;
  - edicao;
  - remocao;
  - produtos sincronizados sem mapeamento.
- Implementadas camadas separadas:
  - repository;
  - service;
  - schemas;
  - rotas API;
  - client do `sync-admin`.
- Regras aplicadas:
  - isolamento por `empresa_id`;
  - `cnpj` deve bater com `empresa_id`;
  - `codigo_produto_local` permanece como chave principal;
  - auditoria administrativa em criacao, atualizacao e remocao.

### Validacao local
- `py -3 -m compileall agent_local backend sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_produto_de_para.py tests\test_sync_admin_rbac.py tests\test_xd_sales_mapper.py tests\test_sync_upsert.py -q` -> `20 passed`.
- `py -3 -m pytest -q` -> `49 passed, 1 skipped`.

### Autorizacoes operacionais
- Arquivo criado:
  - `docs/autorizacoes_operacionais.md`
- Objetivo:
  - registrar autorizacoes recorrentes para Git, SSH, deploy VPS, migrations e validacoes sem rediscutir o fluxo a cada execucao.

### Deploy VPS executado - 2026-04-29
- Branch em producao:
  - `main`
- Commit funcional em producao:
  - `b198512` - `Expand commercial reporting and XD product mapping`
- PR final mergeado:
  - `#21` - `Expand commercial reporting and XD product mapping`
- Commit funcional do deploy:
  - `902bccd` - `feat: expand commercial reporting module`
- Commit de autorizacoes/documentacao:
  - `8f1f9b4` - `docs: record deployment authorization and VPS status`
- Comando executado na VPS:
  - `bash infra/scripts/deploy-prod.sh`
- Resultado do deploy:
  - build backend/frontend OK;
  - containers recriados;
  - migration aplicada com `current_version=6`;
  - `integrado-backend` healthy;
  - `integrado-frontend` healthy;
  - `integrado-nginx` healthy.
- Validacao publica:
  - `https://movisystecnologia.com.br/healthz` -> `200`;
  - `https://movisystecnologia.com.br/readyz/backend` -> `200`;
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `200`;
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `200`.
- Validacao de schema na VPS:
  - `version=6`;
  - `produto_de_para=produto_de_para`;
  - `vendas_detail_columns=5`.
- Validacao de rotas backend na VPS:
  - `/admin/tenants/12345678000199/reports/overview` -> `200`;
  - `/admin/tenants/12345678000199/produto-de-para?limit=1` -> `200`;
  - `/admin/tenants/12345678000199/produto-de-para/unmapped?limit=1` -> `200`.
- Antes do checkout, a VPS tinha alteracoes locais. Elas foram preservadas em stash e em `infra/deploy-safety/`.
- A branch temporaria foi sincronizada com `origin/main` apos o deploy:
  - merge commit local/remoto: `ef3030a`;
  - `py -3 -m pytest -q` -> `49 passed, 1 skipped`;
  - PR `#21` mergeado em `main` com squash;
  - VPS atualizada para `main` e deploy executado novamente;
  - `scripts/db_migrate.py` retornou `no pending migrations (current_version=6)`.
- Ajuste operacional apos deploy:
  - `infra/nginx/default.conf` e `infra/scripts/*` foram restaurados para o estado rastreado em `main`;
  - `nginx -t` OK;
  - `nginx -s reload` OK;
  - health HTTPS continuou `200`.
- Estado Git da VPS apos limpeza:
  - arquivos rastreados limpos;
  - permanecem somente artefatos locais nao versionados:
    - `infra/backups/postgres_20260429_030001.sql.gz`;
    - `infra/deploy-safety/`;
    - `infra/nginx/certs/accounts/`.

## Checkpoint UX relatorios cliente - 2026-04-29

### Entrega local
- Portal cliente `/client/reports` passa a abrir como dashboard resumido.
- Relatorios detalhados passam a ser acessados por atalhos:
  - `report_view=daily_revenue`;
  - `report_view=payments`;
  - `report_view=products`;
  - `report_view=families`;
  - `report_view=terminals`;
  - `report_view=sales`.
- Filtros avancados foram movidos para bloco recolhivel.
- Relatorios dedicados exibem conteudo isolado por assunto, reduzindo poluicao visual.

### Validacao local
- `py -3 -m compileall sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_sync_admin_rbac.py -q` -> `10 passed`.
- `py -3 -m pytest -q` -> `49 passed, 1 skipped`.

### Deploy VPS
- PR:
  - `#23` - `Split client reports into dashboard and drilldown views`
- Commit em producao:
  - `33eb235` - `Split client reports into dashboard and drilldown views`
- Deploy:
  - `bash infra/scripts/deploy-prod.sh`
  - `MIGRATION OK - no pending migrations (current_version=6)`
- Validacao:
  - `integrado-backend` healthy;
  - `integrado-frontend` healthy;
  - `integrado-nginx` healthy;
  - `https://movisystecnologia.com.br/healthz` -> `200`;
  - `https://movisystecnologia.com.br/readyz/backend` -> `200`;
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `200`;
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `200`.
- Ajuste operacional:
  - `infra/nginx/default.conf` restaurado para o estado rastreado;
  - `nginx -t` OK;
  - `nginx -s reload` OK.

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

## Hotfix portal cliente para admin - 2026-04-28

### Problema reportado
- Ao acessar o portal cliente autenticado como admin, a aplicacao retornava:
  - `{"detail":"Acesso restrito ao portal do cliente."}`

### Decisao tecnica
- Admin deve conseguir abrir todos os portais de cliente em modo suporte/validacao.
- Usuario `client` continua restrito ao proprio `empresa_id` e ao proprio escopo de filiais.
- Admin precisa resolver o tenant pelo parametro `empresa_id`, mantendo o isolamento multi-tenant explicito.

### Correcao aplicada
- Novo guard web:
  - `require_client_portal_access`
  - aceita `client` com `empresa_id`;
  - aceita `admin`;
  - rejeita demais perfis.
- Rotas ajustadas para admin preview:
  - `/client/dashboard?empresa_id=<empresa_id>`
  - `/client/reports?empresa_id=<empresa_id>`
  - `/client/reports/export.csv?empresa_id=<empresa_id>`
  - `/client/reports/export.xlsx?empresa_id=<empresa_id>`
  - `/client/reports/export.pdf?empresa_id=<empresa_id>`
- Templates do portal cliente agora exibem aviso de visualizacao administrativa quando o acesso for feito por admin.

### Arquivos principais
- `sync-admin/app/web/deps.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/client_dashboard.html`
- `sync-admin/app/templates/client_reports.html`
- `tests/test_sync_admin_rbac.py`

### Validacao local
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### Deploy VPS
- Branch em producao:
  - `codex/restore-backend-reporting-contract`
- Commit em producao:
  - `c258d71` - `fix: allow admin client portal preview`
- Deploy executado com sucesso via:
  - `bash infra/scripts/deploy-prod.sh`
- Containers validados como saudaveis:
  - `integrado-backend`
  - `integrado-frontend`
  - `integrado-nginx`
  - `integrado-db`

### Links operacionais
- Portal cliente como admin:
  - `https://movisystecnologia.com.br/admin/client/dashboard?empresa_id=12345678000199`
- Relatorios cliente como admin:
  - `https://movisystecnologia.com.br/admin/client/reports?empresa_id=12345678000199`

### Estado Git
- Branch local atual:
  - `codex/restore-backend-reporting-contract`
- Ultimo commit:
  - `c258d71` - `fix: allow admin client portal preview`
- Push ja executado para GitHub.
- `gh` local esta sem autenticacao:
  - `gh auth status` -> nao autenticado.

### Pendente obrigatorio
- Reautenticar GitHub CLI ou usar navegador para abrir/atualizar PR.
- Mergear `codex/restore-backend-reporting-contract` em `main`.
- Depois do merge, voltar a VPS para seguir `main` e validar que nao houve downgrade.

## Hotfix navegacao admin para portal cliente - 2026-04-28

### Decisao operacional
- Admin deve ter acesso a todas as telas do sistema, inclusive telas do portal cliente.
- O acesso admin ao portal cliente continua multi-tenant seguro:
  - sempre com `empresa_id` explicito ou fallback operacional `CONTROL_EMPRESA_ID`;
  - perfil `client` continua preso ao proprio tenant.

### Correcao aplicada
- `admin` recebeu permissoes explicitas:
  - `client.dashboard.view`
  - `client.reports.view`
- Menu lateral do admin agora exibe:
  - `Portal Cliente`
  - `Relatórios Cliente`
- Links usam `settings.control_empresa_id` para abrir um tenant padrao sem URL manual.

### Arquivos alterados
- `sync-admin/app/web/deps.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/base.html`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### Controle de conflito PR
- Antes do push foi executado:
  - `git fetch origin`
  - merge de `origin/main`
  - conflito resolvido localmente em `tests/test_sync_admin_rbac.py`
  - suite completa verde
- Commits relevantes:
  - `5844f52` - `fix: expose client portal navigation to admin`
  - `026fa96` - `merge main after admin portal navigation update`
- Push ja executado para `codex/restore-backend-reporting-contract`.

## Modernizacao BI do painel de relatorios - 2026-04-28

### Decisao tecnica
- Evoluir o painel atual sem reescrever o stack para React neste ciclo.
- Manter arquitetura existente:
  - backend central FastAPI/SQLAlchemy;
  - sync-admin em FastAPI + Jinja;
  - graficos via Chart.js;
  - exportacoes existentes preservadas.
- Implementar uma superficie visual de BI comercial com baixo risco e compatibilidade com producao.

### Entregue
- Dashboard de relatorios com visual SaaS/BI:
  - header executivo;
  - filtros globais;
  - cards de KPI;
  - graficos de linha, barra e donut;
  - comparativo com periodo anterior;
  - status da API local;
  - tabela detalhada com busca e ordenacao local;
  - layout responsivo desktop/tablet/celular;
  - tema claro/escuro por toggle.
- KPIs adicionados:
  - total faturado;
  - total de registros;
  - ticket medio;
  - crescimento percentual;
  - periodo anterior;
  - ultima sincronizacao;
  - status da API local.
- Endpoints JSON adicionados no sync-admin:
  - caminho publico usado pela UI/Nginx:
    - `GET /reports/api/dashboard`
    - `GET /reports/api/kpis`
    - `GET /reports/api/charts`
    - `GET /reports/api/table`
    - `GET /reports/api/sync-status`
    - `GET /reports/api/export/pdf`
    - `GET /reports/api/export/excel`
    - `GET /reports/api/export/csv`
  - aliases locais preservados:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/kpis`
  - `GET /api/reports/charts`
  - `GET /api/reports/table`
  - `GET /api/reports/sync-status`
  - `GET /api/reports/export/pdf`
  - `GET /api/reports/export/excel`
  - `GET /api/reports/export/csv`
- Atualizacao automatica:
  - dashboard consulta endpoint JSON em intervalo configurado;
  - atualiza KPIs sem reload completo.
- Drill-down inicial:
  - clique em ponto/barra do grafico filtra a tabela detalhada pelo label selecionado.
- Regra de 14 meses:
  - `_resolve_report_period` agora limita a janela de consulta a `MAX_REPORT_WINDOW_DAYS=427`.
  - se usuario enviar intervalo maior, o inicio e ajustado para respeitar a janela maxima.

### Arquivos alterados
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/static/js/reports.js`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `29 passed, 1 skipped`

### Pendente recomendado
- Validar visual no navegador/VPS apos merge.
- Em ciclo futuro, se necessario, migrar o frontend para React/Recharts com contrato de API ja preparado.

## Hotfix PDF de relatorios - 2026-04-28

### Problema reportado
- PDF de relatorios era gerado como texto corrido e comprimido.
- Conteudo ficava ilegivel:
  - filtros, KPIs, serie diaria, top produtos e vendas recentes saiam quase em bloco unico.

### Correcao aplicada
- `report_to_pdf_bytes` foi refeito para gerar PDF estruturado:
  - titulo;
  - data de geracao;
  - secao de filtros e resumo;
  - secao de indicadores;
  - tabela de serie diaria;
  - tabela de top produtos;
  - tabela de vendas recentes;
  - paginacao automatica quando o conteudo passa do limite da pagina.
- Implementado renderizador PDF interno `_PdfDocument`, sem dependencia externa.

### Arquivos alterados
- `sync-admin/app/services/export_service.py`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `4 passed`
- `py -3 -m pytest -q`
  - Resultado: `30 passed, 1 skipped`

## Hotfix CSV/Excel de relatorios - 2026-04-28

### Problema reportado
- CSV nao estava funcionando.
- Excel estava confuso para o cliente entender.

### Causa
- CSV usava `csv.DictWriter` com campos fixos tecnicos e quebrava quando `recent_items` trazia campos extras.
- Excel exportava abas/cabecalhos tecnicos em ingles:
  - `Overview`
  - `DailySales`
  - `TopProducts`
  - `RecentSales`

### Correcao aplicada
- CSV:
  - passou a ignorar campos extras;
  - usa separador `;`;
  - cabecalhos em portugues:
    - `Data`, `Produto`, `Valor`, `Pagamento`, `Tipo`, `Familia`, `Filial`, `Terminal`, `Codigo`.
- Excel:
  - abas simplificadas:
    - `Resumo`
    - `Vendas`
    - `Produtos`
    - `Dias`
  - cabecalhos em portugues;
  - removeu metricas tecnicas cruas do cliente.

### Arquivos alterados
- `sync-admin/app/services/export_service.py`
- `tests/test_sync_admin_rbac.py`
- `REGISTRO_DE_MUDANCAS.md`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `5 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

## Hotfix 404 Portal Cliente - 2026-04-28

### Problema reportado
- Portal do cliente retornava:
  - `404 Not Found`
  - `nginx/1.27.5`

### Causa
- O Nginx tinha rota para `/client/reports`, mas nao tinha rota para `/client/dashboard`.
- O menu do admin e o login do cliente usam link absoluto `/client/dashboard`.

### Correcao aplicada
- Adicionado no Nginx:
  - `location /client/dashboard { proxy_pass http://frontend_upstream; }`
- Teste de contrato atualizado:
  - `tests/test_production_operations.py`

### Validacao
- `py -3 -m pytest tests/test_production_operations.py -q`
  - Resultado: `8 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

## Padronizacao visual AdminLTE - 2026-04-28

### Decisao tecnica
- AdminLTE passa a ser a base visual oficial do `sync-admin`.
- Todas as telas autenticadas usam:
  - `main-sidebar`;
  - `main-header navbar`;
  - `content-wrapper`;
  - `content-header`;
  - breadcrumbs;
  - `main-footer`;
  - cards, small-boxes, badges, alerts e tabelas no padrao AdminLTE.

### Entregue
- Login migrado para layout AdminLTE (`login-page`, `login-box`, `card-outline`).
- Menu lateral padronizado com:
  - Dashboard;
  - Relatorios;
  - Empresas;
  - Usuarios;
  - APIs conectadas;
  - Sincronizacoes;
  - Logs;
  - Configuracoes;
  - Backup;
  - Sair.
- Relatorios migrados para BI com AdminLTE:
  - KPIs em `small-box`;
  - graficos em `card card-outline`;
  - filtros compactos em card lateral;
  - ranking executivo;
  - tabela responsiva com busca, ordenacao e paginacao local;
  - exportacao CSV, Excel e PDF preservada.
- Criado partial reutilizavel:
  - `sync-admin/app/templates/partials/adminlte_components.html`.
- Filtro de categoria agora tambem e aplicado no backend por produto/familia, sempre com `empresa_id`.

### Arquivos principais
- `sync-admin/app/templates/base.html`
- `sync-admin/app/templates/login.html`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `sync-admin/app/templates/partials/adminlte_components.html`
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/static/js/reports.js`
- `backend/repositories/venda_repository.py`
- `backend/services/tenant_report_service.py`
- `backend/api/routes/tenant_admin.py`
- `sync-admin/app/services/control_service.py`
- `sync-admin/app/web/routes/pages.py`

### Validacao
- `py -3 -m compileall sync-admin/app backend`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py tests/test_sync_upsert.py tests/test_sync_admin_sync_cockpit.py -q`
  - Resultado: `14 passed`
- `py -3 -m pytest -q`
  - Resultado: `33 passed, 1 skipped`

## Checkpoint visual AdminLTE em producao - 2026-04-28

### Contexto
- O painel de relatorios foi padronizado com AdminLTE, mas a validacao visual real mostrou problemas de proporcao:
  - KPIs estreitos/verticais;
  - filtros laterais com overflow horizontal;
  - cabecalho `Filtros globais` e resumo de chips estourando a largura do card.

### Correcoes aplicadas
- `fix: normalize AdminLTE report layout proportions`
  - Commit: `8a7bdb9`
  - Corrigiu proporcao dos KPIs e conflitos entre grid proprio e `.row` do AdminLTE.
- `fix: prevent report filter sidebar overflow`
  - Commit: `3eaa85d`
  - Corrigiu overflow horizontal do painel lateral de filtros.
  - Ajustou inputs/selects, grid compacto e chips verticais.
- `fix: contain report filter header overflow`
  - Commit: `7cc6729`
  - Corrigiu estouro do cabecalho `Filtros globais`.
  - Isolou classe `bi-filter-head`.
  - Ajustou `card-title`, descricao e chips de resumo com reticencias.

### Arquivos principais
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/templates/partials/report_dashboard_content.html`

### Validacao
- `py -3 -m compileall sync-admin\app`
  - OK
- Deploy VPS aplicado na branch:
  - `codex/restore-backend-reporting-contract`
- VPS atualizada para:
  - `7cc6729`
- Containers validados:
  - `integrado-frontend` healthy
  - `integrado-nginx` healthy
- Smoke externo:
  - `https://movisystecnologia.com.br/healthz`
  - Resultado: `ok`

### Estado atual para retomada
- Workspace local estava limpo antes deste checkpoint documental.
- Producao esta alinhada com a branch `codex/restore-backend-reporting-contract`.
- O bug visual reportado do bloco `Filtros globais` foi tratado no CSS e publicado.
- Proxima acao recomendada:
  - validar visual no navegador em `https://movisystecnologia.com.br/client/dashboard`;
  - se estiver aprovado, abrir/atualizar PR para merge em `main`;
  - apos merge, manter VPS seguindo `main`.

## Evolucao API Local - painel de banco por formulario - 2026-04-28

### Decisao
- Manter a arquitetura correta para cliente real:
  - credenciais do banco ficam no agente local;
  - API web recebe apenas dados sincronizados;
  - admin web acompanha status e pode operar a API conectada;
  - cliente nao precisa editar JSON para configurar o banco.

### Entregue
- Criado servico local de configuracao de banco:
  - `agent_local/config/database_config.py`
- Painel local `agent_local/pairing_ui.py` evoluido para `MoviSync - Painel Local`.
- Nova aba `Banco Local` com:
  - tipo do banco;
  - host/IP;
  - porta;
  - nome do banco;
  - usuario;
  - senha;
  - SSL;
  - intervalo de sincronizacao;
  - tamanho do lote;
  - arquivo `.env`.
- Botoes adicionados:
  - `Testar banco`;
  - `Salvar banco`.
- O painel salva automaticamente:
  - `AGENT_MARIADB_URL`;
  - `SYNC_INTERVAL_MINUTES`;
  - `BATCH_SIZE`.
- Instalador local atualizado para criar tambem:
  - `Abrir_Painel_Local.cmd`
- Atalho antigo preservado:
  - `Abrir_Vinculacao.cmd`

### Arquivos principais
- `agent_local/config/database_config.py`
- `agent_local/pairing_ui.py`
- `infra/client-agent/install-agent-client.ps1`
- `infra/client-agent/README.md`
- `infra/client-agent/RELEASES.md`
- `tests/test_agent_local_database_config.py`

### Validacao
- `py -3 -m compileall agent_local`
  - OK
- `py -3 -m pytest tests\test_agent_local_database_config.py tests\test_agent_pairing_service.py -q`
  - Resultado: `3 passed`
- `py -3 -m pytest -q`
  - Resultado: `35 passed, 1 skipped`
- Smoke de pacote instalador:
  - `powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1 -VersionTag local-panel-smoke -OutputRoot .\output\client-agent-releases`
  - Resultado: release gerada em `output/client-agent-releases/local-panel-smoke`

### Proximo passo recomendado
- Commitar e publicar esta evolucao.
- Depois criar release versionada oficial do instalador se for distribuir para cliente.

## Teste ponta a ponta MariaDB local -> API web -> relatorios - 2026-04-28

### Objetivo
- Validar o fluxo real solicitado:
  - banco MariaDB local;
  - agente/API local;
  - envio para API web em producao;
  - visualizacao posterior no portal do cliente.

### Ambiente usado
- Branch local:
  - `codex/local-agent-db-panel`
- API web:
  - `https://movisystecnologia.com.br/admin/api`
- Tenant:
  - `12345678000199`
- Banco local:
  - MariaDB em `127.0.0.1:3308/xd`
- Query local:
  - `AGENT_SOURCE_QUERY` do `agent_local/.env.example`
- Checkpoint runtime local:
  - `agent_local/data/checkpoints.json`
- Chave runtime local:
  - `agent_local/data/agent_api_key.txt`
  - adicionada ao `.gitignore` para nunca versionar.

### Passos executados
- Criado codigo temporario de pareamento na VPS para o tenant `12345678000199`.
- Ativado o agente local com o codigo gerado.
- Gerada chave local do agente em `agent_local/data/agent_api_key.txt`.
- Configuracao MariaDB salva no `.env` local via novo servico do painel:
  - `AGENT_MARIADB_URL`;
  - `AGENT_SOURCE_QUERY`;
  - `SYNC_INTERVAL_MINUTES`;
  - `BATCH_SIZE`;
  - `CHECKPOINT_FILE`.
- Teste de conexao MariaDB:
  - `mariadb_ping=True`
- Amostra antes do envio:
  - havia registros pendentes apos checkpoint `2026-01-14T11:17:44+00:00`.
- Rodado ciclo unico do `SyncRunner`.

### Resultado da sincronizacao
- API web retornou:
  - `status`: `ok`
  - `empresa_id`: `12345678000199`
  - `inserted_count`: `484`
  - `updated_count`: `0`
  - `processed_count`: `484`

### Resultado do relatorio web
- Endpoint administrativo de relatorios em producao confirmou:
  - periodo: `2026-01-14` ate `2026-04-28`
  - `total_records`: `485`
  - `total_sales_value`: `20132.21`
  - `distinct_products`: `103`
  - `first_sale_date`: `2026-01-14`
  - `last_sale_date`: `2026-04-22`

### Links para verificar visualmente
- Portal cliente:
  - `https://movisystecnologia.com.br/client/dashboard?empresa_id=12345678000199`
- Relatorios cliente com periodo usado no teste:
  - `https://movisystecnologia.com.br/client/reports?empresa_id=12345678000199&start_date=2026-01-14&end_date=2026-04-28`

### Cuidados tomados
- A chave local do agente nao foi exibida no log.
- A chave local do agente foi ignorada no Git:
  - `.gitignore`
  - `agent_local/data/agent_api_key.txt`
- O checkpoint runtime alterado pelo teste nao foi commitado.

### Commits relacionados
- `e6a4b7d` - `feat: add local agent database setup panel`
- `f3ba66e` - `chore: ignore local agent runtime key`

### Estado para continuar depois
- O fluxo local -> web esta provado com dados reais.
- A branch `codex/local-agent-db-panel` esta publicada.
- PR ainda precisa ser aberta/mergeada na `main`.
- Proximo passo seguro:
  - abrir PR de `codex/local-agent-db-panel` para `main`;
  - apos merge, atualizar VPS para `main`;
  - gerar release versionada oficial do instalador do cliente.

## Checkpoint: primeira carga canonica enriquecida - 2026-04-28

### Objetivo
- Ao configurar a API local, a primeira carga deve transformar o MariaDB local em modelo canonico para relatorios.
- O agente local nao deve enviar estrutura bruta do banco.
- A API web deve receber dimensoes necessarias para BI:
  - `forma_pagamento`;
  - `familia_produto`;
  - `tipo_venda`;
  - `terminal_code`;
  - `branch_code`;
  - metadados de origem (`cnpj`, `company_name`, `payment_methods`).

### Entrega
- Criado auto-mapeamento `AGENT_SOURCE_QUERY=auto`.
- Quando detectar `salesdocumentsreportview`, o agente monta query canonica automaticamente.
- Familia de produto vem de `itemsgroups`.
- Forma de pagamento vem de `invoicepaymentdetails` + `xconfigpaymenttypes`.
- O payload `/sync` passou a preservar campos de relatorio no envio.
- O backend passou a aceitar `source_metadata`.
- O backend rejeita `source_metadata.cnpj` diferente do tenant autenticado.
- O backend atualiza `Tenant.nome` quando a origem local informar `company_name`.

### Validacao
- Teste unitario/local:
  - `py -3 -m pytest -q`
  - resultado: `40 passed, 1 skipped`
- Teste real contra MariaDB local:
  - `source_query=auto`;
  - retornou registro com `branch_code`, `terminal_code`, `tipo_venda`, `forma_pagamento` e `familia_produto`;
  - metadados retornaram `cnpj` e `payment_methods`;
  - `payment_methods_count=7`.

### Proximo passo seguro
- Commitar a entrega.
- Abrir/atualizar PR da branch `codex/local-agent-db-panel`.
- Depois do merge, atualizar VPS.

## Checkpoint: usuario cliente padrao e portal separado - 2026-04-28

### Entrega
- Seed automatico do usuario cliente:
  - usuario: `adm`;
  - perfil: `client`;
  - escopo: `company`;
  - empresa padrao: `CONTROL_EMPRESA_ID`;
  - senha configurada por `INITIAL_CLIENT_PASSWORD` e armazenada somente como hash no banco.
- Criado login separado do portal do cliente:
  - `/client/login`;
  - publico via Nginx em `/MoviRelatorios/login`.
- Cliente autenticado vai para:
  - `/client/reports`.
- Cliente nao acessa dashboard/admin:
  - `/dashboard` retorna `403` para perfil `client`.
- Admin continua podendo visualizar o portal cliente para suporte/teste.
- Nginx passou a mapear:
  - `/MoviRelatorios/*` -> `/client/*`;
  - `/admin/*` permanece separado.

### Validacao
- Testes focados:
  - `py -3 -m pytest tests\test_sync_admin_rbac.py tests\test_production_operations.py -q`
  - `15 passed`
- Suite completa:
  - `py -3 -m pytest -q`
  - `40 passed, 1 skipped`
