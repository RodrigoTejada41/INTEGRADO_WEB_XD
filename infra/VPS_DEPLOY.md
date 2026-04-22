# Deploy em VPS (Producao e dev)

## Fluxo operacional padrao
O ciclo recomendado para qualquer alteracao relevante e:
1. Fazer a mudanca local.
2. Rodar os testes afetados.
3. Atualizar a documentacao de continuidade se houver impacto duradouro.
4. Subir primeiro para a VPS de `dev`.
5. Validar health e readiness na VPS.
6. Promover para producao apenas depois de aprovado em `dev`.

## 1. Pre-requisitos da VPS
- Ubuntu/Debian com acesso SSH.
- Docker e Docker Compose instalados.
- Repositorio clonado na VPS.

## 1.1. Ambiente `dev`
Para a VPS de desenvolvimento, mantenha um `APP_DIR` separado do ambiente de producao e um `.env.prod` proprio.

Recomendacao:
- usar outro hostname ou subdominio, se disponivel
- usar portas distintas de producao quando o host compartilhar a mesma VPS
- manter segredos, banco e tokens separados de producao
- validar sempre com `curl` apos o deploy

## 2. Estrutura criada
- `docker-compose.prod.yml`
- `infra/SSH_ACESSO.md`
- `infra/nginx/default.conf`
- `infra/nginx/ssl-example.conf`
- `infra/scripts/setup-vps.sh`
- `infra/scripts/deploy-prod.sh`
- `infra/scripts/update.sh`
- `infra/scripts/backup-db.sh`
- `infra/scripts/restore-db.sh`
- `.github/workflows/deploy-prod.yml`

## 3. Primeira configuracao na VPS
```bash
cd /opt
git clone <URL_DO_REPOSITORIO> integrado_web_xd
cd integrado_web_xd
bash infra/scripts/setup-vps.sh
cp .env.prod.example .env.prod
```

Edite o `.env.prod` com senhas reais:
- `POSTGRES_PASSWORD`
- `ADMIN_TOKEN`
- `BACKEND_SECRET_KEY`
- `FRONTEND_SECRET_KEY`
- `INITIAL_ADMIN_PASSWORD`
- `CORS_ALLOWED_ORIGINS`

## 3.1. Usuario dedicado para deploy SSH
Recomendacao de producao: usar um usuario dedicado, por exemplo `deploy`, em vez de reutilizar usuario administrativo.

Exemplo de preparo na VPS:
```bash
cd /opt/integrado_web_xd
export DEPLOY_USER=deploy
export APP_DIR=/opt/integrado_web_xd
export DEPLOY_PUBLIC_KEY="<COLE_AQUI_A_CHAVE_PUBLICA>"
export DEPLOY_FROM=""
bash infra/scripts/setup-deploy-user.sh
```

O script:
- cria o usuario dedicado de deploy
- adiciona o usuario ao grupo `docker`
- instala a chave publica em `authorized_keys`
- restringe a chave para executar apenas `infra/scripts/update.sh`
- desabilita `pty`, port forwarding, agent forwarding e `X11`

Se quiser limitar a origem da chave, defina `DEPLOY_FROM`:
```bash
export DEPLOY_FROM="203.0.113.10"
```

Ou varias origens:
```bash
export DEPLOY_FROM="203.0.113.10,198.51.100.20"
```

## 3.2. Importante: chave somente neste computador
Isso depende de onde o deploy e executado:

- Se o deploy automatico continuar no GitHub Actions com `ubuntu-latest`, a chave `VPS_SSH_KEY` **nao pode ser limitada a este computador**, porque a conexao sai dos runners do GitHub, nao da sua maquina.
- Se voce quer que a chave seja utilizavel apenas a partir deste computador, use uma destas abordagens:
  - deploy manual a partir deste computador com uma chave local exclusiva
  - runner `self-hosted` nesta maquina e workflow apontando para esse runner

Para o modelo atual com runner hospedado pelo GitHub, a protecao recomendada e:
- usuario dedicado de deploy
- chave restrita por comando em `authorized_keys`
- opcionalmente restringir por IP apenas se voce migrar para `self-hosted runner` ou deploy manual

## 4. Deploy manual
```bash
cd /opt/integrado_web_xd
bash infra/scripts/deploy-prod.sh
```

Se este for o ambiente `dev`, prefira:
```bash
export APP_DIR=/opt/integrado_web_xd-dev
bash infra/scripts/deploy-prod.sh
```

Validacao:
```bash
curl -f http://127.0.0.1/healthz
curl -f http://127.0.0.1/api/health/ready
```

## 5. Atualizacao de versao
```bash
cd /opt/integrado_web_xd
bash infra/scripts/update.sh
```

## 6. Backup e restore
Backup:
```bash
cd /opt/integrado_web_xd
bash infra/scripts/backup-db.sh
```

Restore:
```bash
cd /opt/integrado_web_xd
bash infra/scripts/restore-db.sh /opt/integrado_web_xd/backups/<arquivo>.dump
```

## 7. GitHub Actions deploy automatico
Workflow: `.github/workflows/deploy-prod.yml`

Configure os secrets no GitHub:
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT` (opcional, default 22)
- `VPS_APP_DIR` (opcional, default `/opt/integrado_web_xd`)

Fluxo:
1. Push em `main`
2. Action conecta via SSH
3. Executa `infra/scripts/update.sh`
4. Atualiza codigo + rebuild + restart + health check

Para `dev`, use o workflow manual ou um branch dedicado ao ambiente de desenvolvimento, mantendo o deploy de `main` reservado para o ciclo de producao.

Workflow dedicado para `dev`:
- `.github/workflows/deploy-dev.yml`

Secrets esperados para `dev`:
- `DEV_VPS_HOST`
- `DEV_VPS_USER`
- `DEV_VPS_SSH_KEY`
- `DEV_VPS_PORT` (opcional, default 22)
- `DEV_VPS_APP_DIR` (opcional, default `/opt/integrado_web_xd-dev`)
- `DEV_VPS_BRANCH` (opcional, default `dev`)

Recomendacao:
- use `VPS_USER=deploy`
- use uma chave exclusiva para deploy, sem reaproveitar chave pessoal de administracao
- se migrar para runner `self-hosted`, entao voce pode limitar a chave ao IP/host dessa maquina

## 7.0. Alternativa: deploy `self-hosted` nesta maquina
Se voce quer que a chave de deploy seja utilizavel apenas a partir deste computador, use manualmente o workflow:
- [deploy-prod-self-hosted.yml](E:\Projetos\INTEGRADO_WEB_XD\.github\workflows\deploy-prod-self-hosted.yml)

Documentacao operacional:
- [SELF_HOSTED_RUNNER_RECOVERY.md](E:\Projetos\INTEGRADO_WEB_XD\infra\SELF_HOSTED_RUNNER_RECOVERY.md)

Esse modo melhora:
- controle de origem do deploy
- possibilidade de usar chave exclusiva desta maquina
- recuperacao planejada apos formatacao

Observacao operacional:
- o deploy automatico principal em `main` permanece centralizado em `.github/workflows/deploy-prod.yml`
- a variante `self-hosted` fica preservada para uso manual e contingencia, evitando execucoes duplicadas em push

## 7.1. Rotacao segura da `VPS_SSH_KEY`
Use este procedimento para trocar a chave sem interromper o deploy:

1. Gere uma nova chave exclusiva para deploy.
```bash
ssh-keygen -t ed25519 -C "deploy-integrado-web-xd" -f ./deploy_integrado_web_xd
```

2. Adicione a nova chave publica na VPS mantendo a antiga temporariamente.
```bash
export DEPLOY_USER=deploy
export APP_DIR=/opt/integrado_web_xd
export DEPLOY_PUBLIC_KEY="$(cat ./deploy_integrado_web_xd.pub)"
bash infra/scripts/setup-deploy-user.sh
```

3. Atualize o secret `VPS_SSH_KEY` no GitHub com a nova chave privada.

4. Execute um deploy de teste por `workflow_dispatch`.

5. Valide:
```bash
curl -f http://127.0.0.1/healthz
curl -f http://127.0.0.1/api/health/ready
```

6. Remova a chave antiga de `authorized_keys`.

7. Registre a data da rotacao e a proxima janela planejada.

Boas praticas:
- usar chave exclusiva por ambiente
- nunca reutilizar chave pessoal de operador
- rotacionar imediatamente em caso de suspeita de vazamento
- guardar a chave privada apenas no GitHub Secret ou em cofre seguro

## 7.2. Checklist de endurecimento SSH
- criar usuario dedicado `deploy`
- desabilitar uso de usuario administrativo para deploy automatico
- restringir a chave por `command=`
- desabilitar `port-forward`, `agent-forward`, `pty` e `X11`
- usar `known_hosts` com `StrictHostKeyChecking=yes`
- manter chave exclusiva para este repositorio/ambiente
- usar `DEPLOY_FROM` se o deploy sair sempre de IP fixo ou de runner `self-hosted`

## 7.3. Checklist de renovacao do certificado HTTPS
Certificado atual informado: **validade ate 19/07/2026**.

Janela recomendada:
- revisar renovacao com 60 dias de antecedencia
- executar renovacao com 30 dias de antecedencia
- validar novamente 7 dias antes do vencimento

Checklist:
1. Confirmar dominio e DNS apontando corretamente para a VPS.
2. Confirmar onde o certificado esta instalado e qual o metodo de emissao/renovacao.
3. Gerar ou renovar o certificado.
4. Instalar certificado e cadeia completa no Nginx.
5. Validar configuracao:
```bash
sudo nginx -t
```
6. Recarregar Nginx:
```bash
sudo systemctl reload nginx
```
7. Validar externamente:
```bash
curl -Iv https://SEU_DOMINIO
openssl s_client -connect SEU_DOMINIO:443 -servername SEU_DOMINIO </dev/null 2>/dev/null | openssl x509 -noout -dates -issuer -subject
```
8. Confirmar `notAfter` novo e registrar a nova data de vencimento.
9. Validar a aplicacao:
```bash
curl -f https://SEU_DOMINIO/healthz
curl -f https://SEU_DOMINIO/api/health/ready
```
10. Confirmar redirecionamento de HTTP para HTTPS, se aplicavel.

Riscos que este checklist evita:
- expiracao do certificado em producao
- alerta de navegador para usuarios
- indisponibilidade do painel/admin/API publica
- renovacao apressada sem validacao de cadeia e Nginx

## 8. Seguranca aplicada
- Banco sem porta publica no host.
- Backend sem porta publica direta no host.
- Exposicao publica apenas via Nginx (`80`).
- Segredos em `.env.prod` e GitHub Secrets.
- Base pronta para HTTPS (arquivo `infra/nginx/ssl-example.conf`).
- Fluxo preparado para usuario dedicado de deploy com chave SSH restrita por comando.
