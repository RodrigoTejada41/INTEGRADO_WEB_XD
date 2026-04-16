# Release Checkpoint v0.1.0

## Versao
- `v0.1.0`
- Data: 2026-04-15

## Status
- Entrega funcional concluida para ingestao + painel administrativo.
- Ambiente validado localmente em Docker.

## Escopo fechado nesta release
- API de recebimento de sincronizacao pronta.
- Persistencia em PostgreSQL pronta.
- Painel administrativo pronto com visao operacional.
- Seguranca base (sessao + hash de senha + API key) ativa.
- Documentacao tecnica e operacional consolidada.

## Comandos de retomada
```powershell
cd sync-admin
Copy-Item .env.example .env
docker compose --env-file .env up -d --build
```

## Validacoes rapidas
1. `GET http://localhost:8080/health` deve retornar `{\"status\":\"online\"}`.
2. Login no painel: `http://localhost:8080/login`.
3. Envio de lote em `POST /api/sync-data` com `X-API-Key`.
4. Conferir dashboard e historico no painel.

## Riscos abertos (pos-release)
- Falta de RBAC completo no painel por perfil.
- Falta de exportacao Excel/PDF.
- Falta de rate limit na API de ingestao.
- Falta de trilha de auditoria estendida para administracao.

## Proxima release sugerida
- `v0.2.0` com foco em:
  - multiempresa/multiusuario
  - RBAC
  - exportacao Excel/PDF
  - monitoramento avancado
