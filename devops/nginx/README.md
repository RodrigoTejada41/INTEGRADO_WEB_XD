# Nginx

Fonte operacional atual:
- configuracao principal: [`infra/nginx/default.conf`](E:\Projetos\INTEGRADO_WEB_XD\infra\nginx\default.conf)
- exemplo HTTPS: [`infra/nginx/ssl-example.conf`](E:\Projetos\INTEGRADO_WEB_XD\infra\nginx\ssl-example.conf)

Uso no deploy atual:
- [`docker-compose.prod.yml`](E:\Projetos\INTEGRADO_WEB_XD\docker-compose.prod.yml) monta `infra/nginx/default.conf` no container `nginx`

Observacao:
- esta pasta e apenas ponto de descoberta e documentacao
- alteracoes operacionais reais de Nginx permanecem em `infra/nginx/`
