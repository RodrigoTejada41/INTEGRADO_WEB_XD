# Changelog

## v0.2.0 - 2026-04-16

### Added
- Role-based access control for the admin panel with `admin`, `analyst`, and `viewer` profiles.
- User creation and listing inside the panel.
- Path handling fixes for test and import stability on Windows.
- Full test suite stabilized at `9 passed`.
- Backend base for tenant-scoped source and destination configuration management.
- Tenant-scoped scheduler support prepared on the backend with persisted source intervals.

### Planned
- Multi-company isolation across company, branch, and terminal scopes.
- Excel and PDF exports.
- Advanced monitoring and operational alerting.
- Expanded administrative audit trail.

## v0.1.0 - 2026-04-15

### Added
- Arquitetura modular completa (`api`, `web`, `models`, `repositories`, `services`, `core`, `config`).
- Endpoint de ingestao `POST /api/sync-data` com validacao de payload e autenticacao por `X-API-Key`.
- Persistencia de lotes e registros (`sync_batches`, `sync_records`) com rastreio de IP, status e quantidade.
- Painel administrativo com login/sessao, dashboard, registros, historico e configuracoes.
- Grafico de movimentacao (Chart.js) e exportacao CSV.
- Stack Docker com 3 servicos:
  - `sync_db` (PostgreSQL)
  - `sync_api` (FastAPI)
  - `sync_web` (Nginx)
- Pacote de documentacao operacional e tecnica em `docs/`.

### Security
- Senhas com hash (`bcrypt` + `passlib`).
- Sessao para rotas administrativas.
- Chave de integracao armazenada por hash.
- Segredos externalizados via `.env`.

### Docs
- Dossie de status da entrega: `docs/12-DOSSIE-STATUS-ATUAL.md`.
- Fluxograma operacional atual: `docs/13-FLUXOGRAMA-ATUAL.md`.

### Notes
- `CEREBRO_VIVO` definido como base de consulta (fora da ingestao do projeto).
- Fonte de processamento focada em `ENGENHARIA_REVERSA`.
