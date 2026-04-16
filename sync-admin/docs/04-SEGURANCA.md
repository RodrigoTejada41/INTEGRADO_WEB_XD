# Seguranca

## Painel web
- Login via formulario (`/login`).
- Sessao com `SessionMiddleware`.
- Rotas administrativas protegidas por sessao (`require_web_user`).
- Senhas armazenadas com hash `bcrypt` (`passlib`).

## API de integracao
- Autenticacao por chave no header `X-API-Key`.
- Chave armazenada com hash SHA-256 em `integration_keys`.
- Ultimo uso da chave registrado (`last_used_at`).

## Boas praticas aplicadas
- Segredos em `.env`.
- Separacao de camada de autenticacao/negocio.
- Validacao estrita de entrada via schemas.

## Recomendacoes de hardening (proxima fase)
- HTTPS obrigatorio (TLS no Nginx).
- Rotacao de API key e trilha de revogacao.
- CSRF protection para formularios web.
- Rate limiting para rota de ingestao.
- Auditoria dedicada para acoes administrativas.
