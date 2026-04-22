# Registro de Mudanças

## v0.2.0 - 2026-04-16

### Adicionado
- Controle de acesso baseado em papéis no painel administrativo, com perfis `admin`, `analyst` e `viewer`.
- Cadastro e listagem de usuários dentro do painel.
- Correções de tratamento de caminhos para estabilidade de testes e importação no Windows.
- Base no backend para gerenciamento de configuração de origem e destino por tenant.
- Suporte a scheduler por tenant com intervalos persistidos em origem.
- Fila persistente de sync e worker dedicado para processar a execução.
- Configurações de conectores criptografadas em repouso antes do armazenamento.
- Execução real de conectores de origem adicionada ao worker do backend.
- Cobertura de testes ampliada para registro de conectores e execução real de origem.
- Retry com backoff e tratamento de dead-letter para jobs de sync.
- O painel passou a exibir contadores da fila, jobs mortos e ação manual de retry para administradores.
- O painel e a página de configurações passaram a exibir métricas de entrega em destinos e status de destinos.
- A página de configurações passou a exibir a trilha de auditoria com detalhes de ator e ação.
- Suíte completa estabilizada em `13 passed`.

### Planejado
- Isolamento multiempresa entre empresa, filial e terminal.
- Exportação para Excel e PDF.
- Monitoramento avançado e alertas operacionais.
- Trilhas de auditoria administrativa ampliadas.

## v0.1.0 - 2026-04-15

### Adicionado
- Arquitetura modular completa (`api`, `web`, `models`, `repositories`, `services`, `core`, `config`).
- Endpoint de ingestão `POST /api/sync-data` com validação de payload e autenticação por `X-API-Key`.
- Persistência de lotes e registros (`sync_batches`, `sync_records`) com rastreio de IP, status e quantidade.
- Painel administrativo com login/sessão, painel de resumo, registros, histórico e configurações.
- Gráfico de movimentação (`Chart.js`) e exportação CSV.
- Pilha Docker com 3 serviços:
  - `sync_db` (PostgreSQL)
  - `sync_api` (FastAPI)
  - `sync_web` (Nginx)
- Pacote de documentação operacional e técnica em `docs/`.

### Segurança
- Senhas com hash (`bcrypt` + `passlib`).
- Sessão para rotas administrativas.
- Chave de integração armazenada por hash.
- Segredos externalizados via `.env`.

### Documentação
- Dossiê de status da entrega: `docs/12-DOSSIE-STATUS-ATUAL.md`.
- Fluxograma operacional atual: `docs/13-FLUXOGRAMA-ATUAL.md`.

### Observações
- `CEREBRO_VIVO` definido como base de consulta fora da ingestão do projeto.
- Fonte de processamento focada em `ENGENHARIA_REVERSA`.
