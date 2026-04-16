# Troubleshooting

## `401 Missing X-API-Key`
- Verificar header `X-API-Key` na requisicao.

## `401 Invalid integration key`
- Verificar valor de `INTEGRATION_API_KEY` no `.env`.
- Reiniciar API para bootstrap da chave inicial.

## API sobe e web cai
- Verificar `nginx/default.conf` sem BOM e com `proxy_pass http://api:8000;`.

## Erro de sessao/login
- Verificar `SECRET_KEY` no `.env`.
- Limpar cookies do navegador e testar novamente.

## Nao conecta no banco
- Verificar `DATABASE_URL`.
- Verificar `db` healthy (`docker compose ps`).
