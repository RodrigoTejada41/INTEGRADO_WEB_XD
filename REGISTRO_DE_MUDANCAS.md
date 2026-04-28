# Registro de Mudanças

> Este registro deve ser lido em conjunto com [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) para manter o mesmo padrão de atuação e documentação.

## v0.2.0 - Em andamento

### Entregue
- Estrutura de deploy VPS em producao consolidada com:
  - `docker-compose.prod.yml`
  - `infra/nginx/default.conf`
  - scripts operacionais em `infra/scripts/*`
  - workflow de deploy via GitHub Actions em `.github/workflows/deploy-prod.yml`
- Dominio e HTTPS ativos com Nginx reverso, separando:
  - cliente em `/MoviRelatorios`
  - API em `/admin`
- Correcao de documentacao da API em producao:
  - `https://movisystecnologia.com.br/admin/docs` voltou a carregar com sucesso
  - roteamento de `/openapi.json` e `/docs/oauth2-redirect` ajustado no Nginx
- Processo de retomada formalizado com checkpoint em `RETOMADA_EXATA.md`.
- RBAC real no painel administrativo, com perfis `admin`, `analyst` e `viewer`.
- Cadastro de usuários no painel com validação de perfil.
- Ajustes de infraestrutura para execução confiável em teste e desenvolvimento.
- Cadastro de `source_configs` e `destination_configs` por tenant no backend.
- Registro inicial de conectores para validar tipos suportados antes de persistir.
- Scheduler por tenant com intervalo persistido em `source_configs` e heartbeat de execução.
- Fila persistida de jobs de sync e worker dedicado para processar a execução.
- Criptografia em repouso das credenciais e configurações dos conectores.
- Execução real de conectores de origem no worker, com suporte inicial a MariaDB, API e arquivo.
- Descoberta automática de conectores plugin-like no pacote, sem registro manual centralizado.
- Cobertura de testes para registro de conectores, conector de arquivo e fluxo MariaDB real.
- Retry com backoff e DLQ para jobs falhos da fila de sync.
- Painel administrativo passou a exibir o estado da fila, a DLQ e o reenfileiramento manual de jobs.
- Replicação para destinos configurados adicionada ao worker, com entrega por tenant.
- Métricas de entrega em destinos e painel de destinations configuradas adicionados.
- Endpoints de summary para source e destination por tenant adicionados na API administrativa.
- Auditoria persistente de alterações de configuração com ator, ação e recurso adicionada.
- Suíte automatizada estabilizada com `12 passed`.
- Hotfix de produção registrado em 2026-04-27:
  - `/connected-apis` corrigido no Nginx para não retornar `404`.
  - `/reports` e `/client/reports` corrigidos no Nginx para não retornar `404`.
  - Schema de `vendas` e `vendas_historico` alinhado com relatórios por filial/terminal usando `branch_code` e `terminal_code`.
  - VPS já recebeu migração SQL idempotente e validação autenticada retornou `200` para `connected-apis` e `reports`.
  - Código local está staged na branch `codex/fix-connected-apis-nginx`, faltando commit/push/PR final.
  - Validação local mais recente: `py -3 -m pytest -q` com `26 passed, 1 skipped`.
- Convergência backend/VPS registrada em 2026-04-27:
  - Deploy de `origin/main` na VPS revelou downgrade porque produção possuía endpoints avançados ainda não versionados no `main`.
  - Restaurado contrato backend avançado em `codex/restore-backend-reporting-contract`.
  - Relatórios por tenant, APIs conectadas, pareamento por código, readiness, auditoria correlacionada, métricas HTTP e scheduler/worker avançados voltaram a compor o código versionado.
  - Validação local completa: `py -3 -m pytest -q` com `26 passed, 1 skipped`.
- Evolução de relatórios cliente/admin em 2026-04-27:
  - Relatórios removidos da navegação principal do admin; `/reports` fica como validação técnica.
  - Portal cliente concentra a experiência operacional em `/client/reports`.
  - Novos filtros por período rápido, datas X a Y e horário X a Y.
  - Novas dimensões de venda: tipo de venda, forma de pagamento e família do produto.
  - Novos gráficos por tipo, pagamento, produto, família e série diária.
  - Validação local completa: `py -3 -m pytest -q` com `27 passed, 1 skipped`.
  - Deploy validado na VPS no commit `fd8fb8b`, com migração `v005` aplicada e smoke `reports=200`.
- Hotfix portal cliente/admin em 2026-04-28:
  - Admin agora pode acessar portal e relatórios de qualquer cliente por `empresa_id`.
  - Cliente permanece isolado ao próprio tenant e escopo de filiais.
  - Exportações do portal cliente aceitam preview administrativo com `empresa_id`.
  - Telas exibem aviso de visualização administrativa.
  - Validação local completa: `py -3 -m pytest -q` com `28 passed, 1 skipped`.
  - Deploy validado na VPS no commit `c258d71`.

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

