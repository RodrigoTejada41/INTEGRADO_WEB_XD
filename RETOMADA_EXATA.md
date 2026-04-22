# RETOMADA EXATA - INTEGRADO_WEB_XD

Data de atualizacao: 2026-04-22

## Objetivo desta nota
Este arquivo e o ponto de entrada para retomar o projeto sem redescobrir contexto.

## Estado atual (validado)
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

