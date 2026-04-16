# Changelog

## v0.1.0 - 2026-04-15

### Adicionado
- Arquitetura modular completa para ingestao, transformacao, persistencia e API.
- API central com autenticacao por chave, validacao de tenant e upsert por `uuid`.
- Agente local para leitura incremental do MariaDB e envio em lote.
- Retencao configuravel com politica de 14 meses na base principal.
- Painel administrativo com login, dashboard, historico, registros e configuracoes.
- Controle de tenant e rotacao de chave via painel.
- Suporte a metricas, health checks e logs operacionais.
- Documentacao tecnica e operacional consolidada.

### Seguranca
- Autenticacao por API key e validacao de `empresa_id`.
- Senhas protegidas por hash.
- Sessao administrativa para o painel.
- Segredos externalizados em arquivo de ambiente.

### Testes
- Cobertura de health checks, login, RBAC, refresh token, logout e upsert multi-tenant.
- Suíte automatizada validada com `8 passed`.

### Observacoes
- O repositório foi versionado com a tag `v0.1.0`.
- O foco desta base e a evolucao incremental para a fase comercial multi-tenant completa.
