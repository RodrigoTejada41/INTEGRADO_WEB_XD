# Segurança

## Painel web
- Login via formulário (`/login`).
- Sessão com `SessionMiddleware`.
- Rotas administrativas protegidas por sessão (`require_web_user`).
- Senhas armazenadas com hash `bcrypt` (`passlib`).

## API de integração
- Autenticação por chave no header `X-API-Key`.
- Chave armazenada com hash SHA-256 em `integration_keys`.
- Último uso da chave registrado (`last_used_at`).

## Boas práticas aplicadas
- Segredos em `.env`.
- Separação entre camada de autenticação e de negócio.
- Validação estrita de entrada por schemas.

## Recomendações de fortalecimento na próxima fase
- HTTPS obrigatório (TLS no Nginx).
- Rotação de API key e trilha de revogação.
- Proteção CSRF para formulários web.
- Limitação de taxa para a rota de ingestão.
- Auditoria dedicada para ações administrativas.
