# Changelog

> Este changelog deve ser lido em conjunto com [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) para manter o mesmo padrão de atuação e documentação.

## v0.2.0 - Em andamento

### Entregue
- RBAC real no painel administrativo, com perfis `admin`, `analyst` e `viewer`.
- Cadastro de usuários no painel com validação de perfil.
- Ajustes de infraestrutura para execução confiável em teste e desenvolvimento.
- Cadastro de `source_configs` e `destination_configs` por tenant no backend.
- Registro inicial de conectores para validar tipos suportados antes de persistir.
- Scheduler por tenant com intervalo persistido em `source_configs` e heartbeat de execução.
- Fila persistida de jobs de sync e worker dedicado para processar a execução.
- Criptografia em repouso das credenciais e configurações dos conectores.
- Execução real de conectores de origem no worker, com suporte inicial a MariaDB, API e arquivo.
- Cobertura de testes para registro de conectores, conector de arquivo e fluxo MariaDB real.
- Retry com backoff e DLQ para jobs falhos da fila de sync.
- Painel administrativo passou a exibir o estado da fila, a DLQ e o reenfileiramento manual de jobs.
- Replicação para destinos configurados adicionada ao worker, com entrega por tenant.
- Métricas de entrega em destinos e painel de destinations configuradas adicionados.
- Endpoints de summary para source e destination por tenant adicionados na API administrativa.
- Auditoria persistente de alterações de configuração com ator, ação e recurso adicionada.
- Suíte automatizada estabilizada com `12 passed`.

### Planejado
- Multiempresa completa com isolamento por empresa, filial e terminal.
- Exportação de planilhas Excel e relatórios em PDF.
- Monitoramento avançado com métricas operacionais mais granulares.
- Camada de auditoria administrativa mais detalhada.

## v0.1.0 - 2026-04-15

### Adicionado
- Arquitetura modular completa para ingestão, transformação, persistência e API.
- API central com autenticação por chave, validação de tenant e upsert por `uuid`.
- Agente local para leitura incremental do MariaDB e envio em lote.
- Retenção configurável com política de 14 meses na base principal.
- Painel administrativo com login, dashboard, histórico, registros e configurações.
- Controle de tenant e rotação de chave via painel.
- Suporte a métricas, health checks e logs operacionais.
- Documentação técnica e operacional consolidada.

### Segurança
- Autenticação por API key e validação de `empresa_id`.
- Senhas protegidas por hash.
- Sessão administrativa para o painel.
- Segredos externalizados em arquivo de ambiente.

### Testes
- Cobertura de health checks, login, RBAC, refresh token, logout e upsert multi-tenant.
- Suíte automatizada validada com `8 passed`.

### Observações
- O repositório foi versionado com a tag `v0.1.0`.
- O foco desta base é a evolução incremental para a fase comercial multi-tenant completa.
