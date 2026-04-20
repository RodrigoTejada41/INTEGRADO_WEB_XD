# Retomada Comercial + VPS - 2026-04-20

Este documento registra o ponto exato para continuar o projeto depois desta fase.

## Estado do GitHub

- Repositorio: `RodrigoTejada41/INTEGRADO_WEB_XD`
- Branch de trabalho atual: `codex-commercial-platform`
- Branch DEV publicada: `dev`
- Pull Request aberta: `https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD/pull/1`
- Status da PR no fechamento deste registro: `Checks passing`
- Ultimo CI verde confirmado:
  - Workflow: `CI`
  - Branch/PR: `codex-commercial-platform`
  - Resultado: `frontend-validate` OK, `backend-tests` OK
- Deploy DEV:
  - Workflow: `Deploy Dev VPS`
  - Branch: `dev`
  - Resultado confirmado no ultimo run: `success`

## O que foi entregue nesta fase

- Backend comercial com autenticacao JWT:
  - login
  - refresh token
  - logout
  - endpoint `me`
- Multi-empresa por CNPJ:
  - tabela `empresas`
  - usuarios vinculados a `empresa_id`
  - protecao de rotas por tenant
- Gestao administrativa:
  - empresas
  - usuarios
  - dashboard inicial
  - auditoria basica
- Banco:
  - migration comercial inicial
  - seed inicial
- Frontend:
  - painel administrativo estatico modular
  - login integrado com JWT
  - dashboard
  - telas de empresas e usuarios
- Infra:
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`
  - Nginx para frontend publico e backend via `/api`
  - scripts de VPS para setup, deploy, update, backup e restore
- CI/CD:
  - CI para backend/frontend
  - deploy automatico DEV na branch `dev`
  - deploy automatico PROD na branch `main`

## Commits importantes desta fase

- `1ad31d4` - plataforma comercial multi-tenant com JWT, painel admin e pipelines VPS
- `6246218` - correcoes iniciais dos workflows
- `c8ae4d3` - CI resiliente com `PYTHONPATH`
- `cad4e6e` - adiciona `jinja2` para testes do `sync-admin`
- `b783829` - adiciona `python-multipart` para formularios FastAPI

## Como rodar localmente

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

URLs locais:

- Frontend: `http://localhost:8080`
- API via Nginx: `http://localhost:8080/api`

Rodar testes:

```bash
pytest -q
```

No Windows, se houver erro de permissao em cache temporario do pytest, usar uma pasta temporaria limpa:

```bash
pytest -q --basetemp .pytest-tmp
```

## Como continuar o fluxo recomendado

1. Revisar a PR #1.
2. Fazer merge da PR #1 em `main` quando quiser promover para producao.
3. Conferir GitHub Secrets antes do deploy real.
4. Validar DEV antes de usar PROD.
5. Depois do merge em `main`, acompanhar o workflow `Deploy Production VPS`.

## Secrets esperados no GitHub

DEV:

- `DEV_VPS_HOST`
- `DEV_VPS_USER`
- `DEV_VPS_SSH_KEY`
- `DEV_VPS_PORT` opcional

PROD:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT` opcional
- `DOMAIN` opcional, recomendado: `movisystecnologia.com.br`
- `LETSENCRYPT_EMAIL` opcional, necessario para HTTPS automatico
- `ENABLE_WWW_DOMAIN` opcional

Importante: nao registrar senha root, token, chave privada ou segredo dentro do repositorio.

## DNS para o dominio

Dominio informado: `MOVISYSTECNOLOGIA.COM.BR`

Registros recomendados no Registro.br quando o DNS estiver liberado:

- Tipo `A`, nome `@`, valor: IP publico da VPS
- Tipo `A`, nome `www`, valor: IP publico da VPS

O Registro.br nao aceita IP como servidor DNS delegado. Para apontar direto para a VPS mantendo DNS do Registro.br, usar a area `Configurar zona DNS` e criar registros `A`.

## Observacoes de seguranca

- A senha de VPS compartilhada durante a conversa deve ser trocada.
- Preferir acesso SSH por chave.
- Desativar login root por senha apenas depois de confirmar que a chave SSH funciona.
- Banco nao deve ser exposto publicamente.
- Backend deve continuar acessivel apenas via Nginx em `/api`.
- Secrets devem ficar no GitHub Secrets e/ou `.env` local da VPS, nunca commitados.

## Arquivos principais para revisar

- `README.md`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy-prod.yml`
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`
- `infra/nginx/default.conf`
- `infra/scripts/setup-vps.sh`
- `infra/scripts/deploy-dev.sh`
- `infra/scripts/deploy-prod.sh`
- `backend/api/routes/auth.py`
- `backend/api/routes/empresas.py`
- `backend/api/routes/usuarios.py`
- `frontend/index.html`

## Proximo trabalho recomendado

- Configurar secrets reais da VPS no GitHub.
- Trocar a senha root da VPS e confirmar SSH por chave.
- Validar o dominio depois da propagacao DNS.
- Fazer merge da PR #1 para `main` quando DEV estiver aceito.
- Testar HTTPS/Let's Encrypt em producao.
