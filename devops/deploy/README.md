# Deploy

Entradas atuais de deploy:
- compose de producao: [`docker-compose.prod.yml`](E:\Projetos\INTEGRADO_WEB_XD\docker-compose.prod.yml)
- runbook da VPS: [`infra/VPS_DEPLOY.md`](E:\Projetos\INTEGRADO_WEB_XD\infra\VPS_DEPLOY.md)
- workflow principal: [`.github/workflows/deploy-prod.yml`](E:\Projetos\INTEGRADO_WEB_XD\.github\workflows\deploy-prod.yml)
- workflow self-hosted manual: [`.github/workflows/deploy-prod-self-hosted.yml`](E:\Projetos\INTEGRADO_WEB_XD\.github\workflows\deploy-prod-self-hosted.yml)

Compatibilidade:
- o caminho principal de operacao passa a ser direto pelo workflow de deploy principal, sem wrapper intermediario

Observacao:
- esta pasta nao substitui `infra/`
- ela consolida o mapa de deploy para operacao e onboarding
