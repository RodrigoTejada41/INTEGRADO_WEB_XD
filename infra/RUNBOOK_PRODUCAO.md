# Runbook de Produção

Este runbook consolida as operações recorrentes da VPS e do stack de produção.

## Objetivo

- subir a aplicação com previsibilidade;
- validar saúde da cadeia `nginx -> backend -> sync-admin -> banco`;
- reduzir erro humano em deploy, backup, restore e rollback;
- manter o site futuro separado das rotas operacionais.

## Rotas operacionais

- Cliente: `/MoviRelatorios`
- Admin: `/admin`
- Health do backend: `/admin/api/health/ready`
- Health do frontend: `/readyz/sync-admin`
- Health do edge: `/healthz`

## Antes de qualquer deploy

```bash
cd /opt/integrado_web_xd
git status --short
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl -f http://127.0.0.1/healthz
curl -f http://127.0.0.1/api/health/ready
curl -f http://127.0.0.1/readyz/sync-admin
```

Confirme:

- `.env.prod` existe e tem segredos reais;
- `POSTGRES_PASSWORD`, `ADMIN_TOKEN`, `BACKEND_SECRET_KEY`, `FRONTEND_SECRET_KEY` e `INITIAL_ADMIN_PASSWORD` nao sao placeholders;
- `docker compose` levanta `db`, `backend`, `frontend` e `nginx` sem erro;
- as rotas `/admin` e `/MoviRelatorios` continuam separadas.

## Deploy manual

```bash
cd /opt/integrado_web_xd
bash infra/scripts/deploy-prod.sh
```

Valide apos o deploy:

```bash
curl -f http://127.0.0.1/healthz
curl -f http://127.0.0.1/api/health/ready
curl -f http://127.0.0.1/readyz/backend
curl -f http://127.0.0.1/readyz/sync-admin
```

## Atualizacao rotineira

```bash
cd /opt/integrado_web_xd
bash infra/scripts/update.sh
```

Use quando:

- houver commit novo em `main`;
- for preciso rebuild/restart completo;
- o deploy automatico falhar por acesso remoto.

## Backup do banco

```bash
cd /opt/integrado_web_xd
bash infra/scripts/backup-db.sh
```

Regras:

- executar antes de troca de schema;
- executar antes de rollback manual;
- manter o arquivo de backup fora do controle de versao.

## Restore do banco

```bash
cd /opt/integrado_web_xd
bash infra/scripts/restore-db.sh /opt/integrado_web_xd/backups/<arquivo>.dump
```

Antes de restaurar:

- confirmar o arquivo de backup correto;
- confirmar o tenant/ambiente afetado;
- parar o fluxo de escrita se necessario;
- validar o estado apos o restore.

## Rollback operacional

1. Identificar o ultimo commit estavel.
2. Reverter o deploy por `update.sh` ou pelo workflow.
3. Confirmar `docker compose ps`.
4. Revalidar health.
5. Conferir painel admin e cliente.

Se o problema for banco:

- restaurar backup valido;
- reenfileirar jobs se necessario;
- nao aplicar rollback cego sem validar schema.

## Falhas mais comuns

- `health/ready` retorna `503`: banco indisponivel, scheduler parado ou `sync-admin` sem controle API.
- `/admin/api` nao aparece no painel: Nginx pode ter perdido o rewrite dedicado.
- `/MoviRelatorios` falha: frontend pode nao estar saudavel ou o Nginx pode estar fora do contrato.
- deploy falha por SSH: chave nao autorizada ou secret invalido.

## Regras de seguranca

- nao salvar chave privada no repositorio;
- nao salvar senha de VPS no repositorio;
- usar segredo externo ou GitHub Secrets;
- manter `backend` sem exposicao direta na porta publica;
- manter `db` sem porta publica.

## Handoff

Outra IA deve ler, nesta ordem:

1. `RETOMADA_EXATA.md`
2. `cerebro_vivo/estado_atual.md`
3. `infra/SSH_ACESSO.md`
4. `infra/VPS_DEPLOY.md`
5. `infra/RUNBOOK_PRODUCAO.md`

Se faltar credencial, parar e informar exatamente qual item falta.
