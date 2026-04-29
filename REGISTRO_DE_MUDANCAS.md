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
- Navegação admin para portal cliente em 2026-04-28:
  - Perfil `admin` recebeu permissões explícitas de portal cliente.
  - Menu lateral do admin agora exibe `Portal Cliente` e `Relatórios Cliente`.
  - Links abrem o tenant padrão configurado por `CONTROL_EMPRESA_ID`.
  - Branch foi sincronizada com `origin/main` antes do push para evitar novo conflito de PR.
- Modernização BI do painel de relatórios em 2026-04-28:
  - Painel de relatórios ganhou layout executivo com KPIs, filtros globais, gráficos, comparativo, status da API local e tabela detalhada.
  - Tema claro/escuro, busca e ordenação local foram adicionados.
  - Endpoints JSON `/reports/api/*` foram criados para atualização automática em produção; aliases `/api/reports/*` ficam preservados para ambiente local.
  - Regra de janela máxima de 14 meses foi aplicada no resolver de período.
  - Validação completa: `py -3 -m pytest -q` com `29 passed, 1 skipped`.
- Hotfix PDF de relatórios em 2026-04-28:
  - Exportação PDF deixou de sair como texto comprimido.
  - Relatório agora possui seções, tabelas e paginação.
  - Validação completa: `py -3 -m pytest -q` com `30 passed, 1 skipped`.
- Hotfix CSV/Excel de relatórios em 2026-04-28:
  - CSV voltou a funcionar ignorando campos extras do backend.
  - CSV e Excel agora usam colunas simples em português para o cliente.
  - Excel passou a ter abas `Resumo`, `Vendas`, `Produtos` e `Dias`.
  - Validação completa: `py -3 -m pytest -q` com `31 passed, 1 skipped`.
- Hotfix Portal Cliente em 2026-04-28:
  - Nginx agora roteia `/client/dashboard` para o `sync-admin`.
  - Corrige `404 Not Found nginx/1.27.5` ao abrir o portal cliente por link absoluto.
  - Validação completa: `py -3 -m pytest -q` com `31 passed, 1 skipped`.
- Padronização AdminLTE global em 2026-04-28:
  - AdminLTE definido como base visual oficial do `sync-admin`.
  - Login, shell autenticado, menu lateral, navbar, content wrapper, breadcrumbs e footer foram padronizados.
  - Relatórios usam `small-box`, `card card-outline`, filtros compactos, gráficos Chart.js, ranking e tabela responsiva.
  - Criado partial reutilizável `partials/adminlte_components.html`.
  - Filtro de categoria agora filtra no backend por produto/família mantendo `empresa_id`.
  - Validação completa: `py -3 -m pytest -q` com `33 passed, 1 skipped`.
- Ajustes visuais AdminLTE pós-deploy em 2026-04-28:
  - Corrigida proporção dos KPIs do dashboard de relatórios.
  - Corrigido overflow horizontal do painel lateral de filtros.
  - Corrigido estouro do cabeçalho `Filtros globais`.
  - Chips de filtros agora respeitam largura e usam reticências para valores longos.
  - Commits publicados:
    - `8a7bdb9` - `fix: normalize AdminLTE report layout proportions`
    - `3eaa85d` - `fix: prevent report filter sidebar overflow`
    - `7cc6729` - `fix: contain report filter header overflow`
  - Deploy VPS aplicado na branch `codex/restore-backend-reporting-contract`.
  - VPS validada no commit `7cc6729`.
  - Health externo validado em `https://movisystecnologia.com.br/healthz` com retorno `ok`.
- Evolução da API Local em 2026-04-28:
  - Painel local renomeado para `MoviSync - Painel Local`.
  - Criada aba `Banco Local` para configurar MariaDB por formulário.
  - Cliente informa host, porta, banco, usuário, senha, SSL, intervalo e lote sem editar JSON.
  - Criado serviço `agent_local/config/database_config.py` para montar URL MariaDB com encoding seguro.
  - Adicionado teste real de conexão MariaDB pelo painel local.
  - Instalador passa a criar `Abrir_Painel_Local.cmd`, mantendo `Abrir_Vinculacao.cmd`.
  - Validação completa: `py -3 -m pytest -q` com `35 passed, 1 skipped`.
  - Smoke de pacote instalador gerado em `output/client-agent-releases/local-panel-smoke`.
- Teste ponta a ponta MariaDB local -> API web -> portal cliente em 2026-04-28:
  - Pareamento local ativado para tenant `12345678000199`.
  - MariaDB local validado em `127.0.0.1:3308/xd`.
  - Ciclo unico do agente enviou `484` registros.
  - API web retornou `inserted_count=484`, `updated_count=0`, `processed_count=484`.
  - Relatorio em producao confirmou `485` registros, total `20132.21`, `103` produtos distintos.
  - Links de validacao:
    - `https://movisystecnologia.com.br/client/dashboard?empresa_id=12345678000199`
    - `https://movisystecnologia.com.br/client/reports?empresa_id=12345678000199&start_date=2026-01-14&end_date=2026-04-28`
  - Chave local `agent_local/data/agent_api_key.txt` foi adicionada ao `.gitignore`.
- Primeira carga canonica enriquecida em 2026-04-28:
  - `AGENT_SOURCE_QUERY=auto` passa a detectar o schema XD local.
  - Agente local monta query canonica sobre `salesdocumentsreportview`.
  - Enriquecimento automatico:
    - forma de pagamento por `invoicepaymentdetails` + `xconfigpaymenttypes`;
    - familia de produto por `itemsgroups`;
    - tipo de venda por `DocumentDescription`;
    - terminal por `Terminal`;
    - filial padrao `0001`.
  - Payload `/sync` preserva dimensoes de relatorio.
  - Payload `/sync` inclui `source_metadata` com `cnpj`, `company_name` quando existir e `payment_methods`.
  - Backend valida que `source_metadata.cnpj` bate com o tenant autenticado.
  - Backend atualiza `Tenant.nome` quando a origem local envia nome da empresa.
  - Validacao completa:
    - `py -3 -m pytest -q` com `40 passed, 1 skipped`;
    - teste real no MariaDB local confirmou dimensoes e `payment_methods_count=7`.
- Usuario cliente padrao e portal separado em 2026-04-28:
  - Seed automatico do usuario cliente `adm` com role `client`.
  - Senha do cliente configurada por `INITIAL_CLIENT_PASSWORD` e armazenada com hash no banco.
  - Criado login separado `/client/login`.
  - Portal publico `/MoviRelatorios/*` agora roteia internamente para `/client/*`.
  - Cliente autenticado redireciona para `/client/reports`.
  - Cliente nao acessa `/dashboard` administrativo.
  - Admin mantem acesso ao portal cliente para suporte/teste.
  - Validacao:
    - testes focados com `15 passed`;
    - suite completa com `40 passed, 1 skipped`.

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

# 2026-04-29 - Relatorios comerciais/financeiros

- Ampliado contrato canonico de vendas com codigo local do produto, familia, categoria, unidade, operador, cliente, status, cancelamento e valores detalhados.
- Criada migration `v006_sales_report_detail_fields`.
- Criada tabela `produto_de_para` separada por empresa.
- Relatorios agora suportam filtros avancados e agrupamentos comerciais/financeiros.
- Exportacoes CSV, Excel e PDF passam a incluir campos detalhados e respeitar filtros avancados.
- Documentacao criada em `docs/relatorios_comerciais_financeiros.md`.
- Validacao: `41 passed, 1 skipped`.

# 2026-04-29 - Referencia XD Software para MariaDB local

- Usado o arquivo `TABELAS DO BANCO XD/REFERENCIA TABELAS BD XD SOFTWARE.xlsx` como base tecnica.
- Agente local passa a suportar fallback automatico por `Documentsbodys + Documentsheaders` quando `salesdocumentsreportview` nao existir.
- Mapeamento preserva `ItemKeyId` como `codigo_produto_local`.
- Pagamento e familia sao enriquecidos por `Invoicepaymentdetails`, `Xconfigpaymenttypes` e `Itemsgroups` quando disponiveis.
- Criadas rotas `GET /settings/xd-mapping` e `GET /settings/xd-mapping/routes` para diagnostico local.
- Validacao: `45 passed, 1 skipped`.

# 2026-04-29 - CRUD DE/PARA Produtos

- Criadas camadas `ProdutoDeParaRepository`, `ProdutoDeParaService` e schemas dedicados.
- Criadas rotas admin para listar, criar/atualizar, editar, remover e consultar produtos sem DE/PARA.
- Tela `/settings` recebeu painel `DE/PARA Produtos` com formulario, listagem, edicao, remocao e produtos pendentes.
- `sync-admin` passou a consumir o CRUD central com `X-Admin-Token` e `X-Audit-Actor`.
- Regras validadas:
  - isolamento por empresa;
  - rejeicao de CNPJ divergente;
  - produto sem mapeamento continua reportavel pelo codigo local;
  - auditoria em mutacoes administrativas.
- `backend.services.__init__` passou a usar lazy import para evitar inicializacao indevida de settings em imports parciais.
- Validacao focada: `20 passed`.
- Suite completa: `49 passed, 1 skipped`.

# 2026-04-29 - Deploy VPS relatorios comerciais

- Deploy executado na VPS em `/opt/integrado_web_xd`.
- Branch em producao apos merge final: `main`.
- PR final: `#21`.
- Commit em producao apos merge final: `b198512`.
- Commit funcional implantado: `902bccd`.
- Commit atual da branch/VPS apos sincronizar com `origin/main`: `ef3030a`.
- Migration aplicada: `current_version=6`.
- Schema validado:
  - tabela `produto_de_para`;
  - colunas detalhadas em `vendas`.
- Rotas validadas:
  - relatorio overview;
  - CRUD/listagem `produto-de-para`;
  - produtos sem DE/PARA.
- Health publico validado com status `200`.
- Nginx rastreado restaurado para o estado de `main`, validado com `nginx -t` e recarregado.

# 2026-04-29 - Autorizacoes operacionais

- Criado `docs/autorizacoes_operacionais.md`.
- Registrado fluxo autorizado para Git, SSH, deploy VPS, migrations e validacoes.

# 2026-04-29 - UX cliente para relatorios configuraveis

- `/client/reports` agora separa dashboard resumido e relatorios dedicados.
- Criadas quick actions para faturamento do dia, pagamentos, produtos, familias, terminais e vendas detalhadas.
- `report_view` controla a visualizacao ativa sem duplicar rotas.
- Filtros avancados foram recolhidos para reduzir poluicao visual.
- Validacao: `49 passed, 1 skipped`.
