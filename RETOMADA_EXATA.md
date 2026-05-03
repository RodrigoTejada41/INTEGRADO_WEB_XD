# RETOMADA EXATA - INTEGRADO_WEB_XD

Data de atualizacao: 2026-05-03

## Checkpoint Menu Inicial Movi_commanda - 2026-05-03

### Implementado
- Identidade visual da UI/API local de comandas trocada para `Movi_commanda`.
- Removidas referencias visuais antigas na UI/API local:
  - `XD`
  - `XD Orders`
  - `XDOrders`
  - `Comandas Locais`
  - `MoviSync`
- Menu inicial mobile criado:
  - marca `Movi_commanda`;
  - visual institucional azul/azul esverdeado;
  - versao do sistema;
  - botoes grandes `USUARIOS`, `DEFINICOES`, `INICIAR`.
- Tela `DEFINICOES` criada com secoes:
  - Servidor;
  - Impressora Bluetooth;
  - Outras configuracoes;
  - Ajuda;
  - Sobre.
- Configuracoes persistidas no SQLite local:
  - `ip_servidor`;
  - `porta_servidor`;
  - `licenca`;
  - `ssid_wifi`;
  - `impressora_bluetooth`;
  - `dpi_impressora`;
  - `largura_impressora`;
  - `caracteres_por_linha`;
  - `tema_interface`;
  - `usuario_logado`;
  - `versao_app`;
  - `codigo_versao`.

### API local adicionada
- `GET /orders/app-info`
- `GET /orders/settings`
- `PUT /orders/settings`
- `POST /orders/settings/test-connection`
- `POST /orders/settings/load-server-data`
- `GET /orders/license`
- `POST /orders/license/validate`

### Banco/configuracao local
- Tabela nova:
  - `local_commanda_settings`
- Versao padrao:
  - `1.0.0`
- Codigo de versao padrao:
  - `100`

### Referencias de tabelas do banco encontradas no projeto
- Fonte principal:
  - `agent_local/db/mariadb_client.py`
  - `agent_local/db/xd_sales_mapper.py`
- Tabelas externas ja mapeadas para catalogo/relatorios:
  - `items`
  - `itemsgroups`
  - `operators`
  - `xconfigoperators`
  - `Documentsbodys`
  - `Documentsheaders`
  - `salesdocumentsreportview`
- Nao foi encontrado contrato externo consolidado para tabelas reais de comanda/pedido. Por isso a operacao de comandas permanece em SQLite local, usando o banco externo para catalogo de usuarios/produtos quando disponivel.

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py -q` -> `9 passed`
- `py -3 -m compileall agent_local -q` -> sem erro
- `py -3 -m pytest -q` -> `78 passed, 1 skipped`
- Busca direcionada em `agent_local/orders/ui.py` e `agent_local/local_api.py` nao encontrou nomes antigos.

## Checkpoint tela principal operacional de comandas - 2026-05-03

### Implementado
- Tela principal `/orders/ui` ajustada no estilo do print:
  - fundo em degrade azul/roxo;
  - avatar do operador logado;
  - nome/perfil do usuario;
  - botoes `CAIXA DE SAIDA` e `MENSAGENS`;
  - botao central `CONTROLE POR VOZ`;
  - grade 3x3 com botoes grandes: `PEDIR`, `ANULAR`, `SUBTOTAL`, `CONTA`, `TRANSFERENCIA`, `PAGAMENTO PARCIAL`, `OUTROS`, `DESCONTO`, `MENU INICIAL`.
- Botoes ligados a fluxos reais:
  - `PEDIR` abre o fluxo comanda/pessoas/mesa/produtos/revisao;
  - `ANULAR` registra anulacao e log;
  - `SUBTOTAL` consulta itens e total parcial;
  - `CONTA` consulta subtotal, descontos, pagamentos parciais, total e saldo;
  - `TRANSFERENCIA` registra transferencia e atualiza mesa/comanda quando aplicavel;
  - `PAGAMENTO PARCIAL` registra pagamento sem fechar a comanda;
  - `DESCONTO` registra desconto fixo ou percentual;
  - `MENSAGENS` e `CAIXA DE SAIDA` consultam tabelas locais;
  - `CONTROLE POR VOZ` tem endpoint preparado com status `planned`.

### API local adicionada
- `GET /orders/me`
- `GET /orders/current`
- `GET /orders/subtotal`
- `GET /orders/account`
- `POST /orders/void`
- `POST /orders/transfer`
- `POST /orders/partial-payment`
- `POST /orders/discount`
- `GET /orders/messages`
- `GET /orders/outbox`
- `POST /orders/voice-command`

### Banco local
- `local_order_operator_permissions`
- `local_order_operation_logs`
- `local_order_messages`
- `local_order_partial_payments`
- `local_order_discounts`
- `local_order_voids`
- `local_order_transfers`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py -q` -> `8 passed`
- `py -3 -m compileall agent_local -q` -> sem erro
- `py -3 -m pytest -q` -> `77 passed, 1 skipped`

### Proximo passo recomendado
1. Instalar release r4 no cliente.
2. Validar visualmente em tablet/celular.
3. Popular permissoes reais dos operadores em `local_order_operator_permissions` quando houver perfis definidos.

## Checkpoint fluxo completo mobile de comandas - 2026-05-03

### Implementado
- API local de comandas mantida separada da API de sync de relatorios.
- Tela `/orders/ui` reescrita para fluxo mobile/tablet:
  - login por usuario carregado do banco local;
  - senha validada por hash PBKDF2;
  - menu principal com `Pedido`, `Consultar comanda`, `Imprimir pre-conta` e `Sair`;
  - abertura de pedido com comanda, quantidade de pessoas e mesa;
  - selecao de familias e produtos em layout responsivo;
  - busca por nome ou codigo;
  - carrinho temporario na tela antes da confirmacao;
  - revisao com `+`, `-`, exclusao individual, observacao por item, lixeira geral e totais;
  - confirmacao envia o pedido para a API local.

### API local adicionada/ajustada
- `GET /orders/users`
- `POST /orders/login`
- `POST /orders/confirm`
- `DELETE /orders/{order_uuid}/items`
- `GET /orders/products?q=...`
- Mutacoes de comanda agora aceitam sessao local por `X-Order-Session`.

### Banco local
- `local_order_operators.password_hash`
- `local_order_sessions`
- `local_orders.people_count`
- Produtos duplicados no mesmo pedido passam a somar quantidade quando codigo e observacao coincidem.

### Arquivos alterados
- `agent_local/orders/repository.py`
- `agent_local/orders/schemas.py`
- `agent_local/orders/service.py`
- `agent_local/orders/ui.py`
- `agent_local/local_api.py`
- `tests/test_agent_local_orders.py`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py -q` -> `7 passed`
- `py -3 -m compileall agent_local -q` -> sem erro
- `py -3 -m pytest -q` -> `76 passed, 1 skipped`

### Proximo passo recomendado
1. Gerar release versionada `v2026-05-03_comandas_r3`.
2. Instalar no cliente e conferir `C:\MoviSyncAgent\VERSAO_INSTALADA.txt`.
3. Validar no tablet/celular `http://127.0.0.1:8765/orders/ui`.
4. Configurar/importar senha hash dos operadores reais antes do uso operacional.

## Checkpoint UI produtos por familia - 2026-05-03

### Implementado
- Tela local de produtos ajustada para operar como a referencia XD:
  - abas horizontais por familia no topo;
  - primeira familia carrega automaticamente;
  - produtos em grade de 3 colunas;
  - botoes grandes com nome do produto em caixa alta;
  - barra inferior com `VER CONTEUDO DA MESA` e `CONCLUIR`.
- Clique no produto:
  - preenche codigo, descricao, preco e quantidade;
  - adiciona direto na comanda selecionada;
  - se nao houver comanda selecionada, bloqueia e mostra aviso.

### Aplicado no cliente instalado
- Backup:
  - `C:\MoviSyncAgent\backup_product_family_ui_20260503_003902`
- Arquivo atualizado:
  - `C:\MoviSyncAgent\agent_local\local_api.py`
- API local reiniciada:
  - `http://127.0.0.1:8765`

### Validacao real no instalado
- `GET /health` -> `{"status":"ok"}`
- `GET /orders/ui` -> HTTP 200
- Tela instalada contem:
  - `product-family-tabs`
  - `product-tile`
  - `VER CONTEUDO DA MESA`
  - `CONCLUIR`
- Familias reais carregadas:
  - `ALCOOLICOS`
  - `BEBIDAS`
  - `BIFUM`
  - `CARE`
  - `DIVERSOS`
  - `ENTRADAS`
  - `FRIOS`
  - `Geral`
  - `LAMEN`
  - `SOBA`
  - `SOBREMESA`
  - `SUSHI`
  - `TEISHOKU`
  - `UDON`
  - `YAKISOBA`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `15 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Proximo passo recomendado
1. Validar visualmente no celular/tablet a tela `http://127.0.0.1:8765/orders/ui`.
2. Selecionar uma comanda aberta e tocar em produtos de familias diferentes.
3. Se necessario, ajustar altura das celulas para o tamanho real da tela usada no restaurante.

## Checkpoint impressao termica local - 2026-05-02

### Implementado
- Renderizacao de cupom termico local para comandas:
  - `GET /orders/{uuid}/thermal-receipt`
  - texto 32 colunas por default
  - inclui comanda, mesa, operador, status, itens, observacoes, total e pagamentos.
- Geracao de job local de impressao:
  - `POST /orders/{uuid}/print`
  - grava arquivo `.txt` em `LOCAL_ORDER_PRINT_JOBS_DIR`
  - retorna `queued` quando impressora fisica nao esta configurada
  - retorna `sent` quando `LOCAL_ORDER_PRINTER_NAME` esta configurado e o Windows aceita o envio via spool.
- Configuracoes adicionadas:
  - `LOCAL_ORDER_PRINT_JOBS_DIR=agent_local/data/print_jobs`
  - `LOCAL_ORDER_RECEIPT_WIDTH=32`
  - `LOCAL_ORDER_PRINTER_NAME=`
- UI local ajustada:
  - texto do botao `PAGAMENTO PARCIAL` corrigido para manter contrato validado por teste.

### Decisao tecnica
- A API nao recebe nome de impressora por requisicao.
- Nome da impressora fica somente em configuracao local.
- Isso reduz risco de execucao indevida e evita acoplamento entre UI e spool do Windows.
- Se a impressora nao estiver definida, o sistema nao perde a impressao: o job fica persistido em arquivo.

### Arquivos alterados
- `agent_local/orders/printer.py`
- `agent_local/orders/service.py`
- `agent_local/orders/schemas.py`
- `agent_local/local_api.py`
- `agent_local/.env.example`
- `tests/test_agent_local_orders.py`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `15 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Proximo passo recomendado
1. Configurar `LOCAL_ORDER_PRINTER_NAME` no cliente instalado com o nome exato da impressora termica do Windows.
2. Aplicar os arquivos no `C:\MoviSyncAgent`.
3. Reiniciar API local.
4. Criar comanda teste e validar `POST /orders/{uuid}/print`.
5. Se houver cozinha/bar, evoluir para impressao de producao por familia/impressora.

## Checkpoint pagamento dividido local - 2026-05-02

### Implementado
- Fechamento de comanda com pagamento dividido.
- Compatibilidade mantida com pagamento unico antigo:
  - `payment_method`
  - `amount_paid`
- Novo formato aceito em `POST /orders/{uuid}/close`:
  - `payments: [{ payment_method, amount }]`
- Persistencia local:
  - tabela `local_order_payments`
  - cada pagamento fica vinculado ao `order_uuid`
- Regras:
  - soma dos pagamentos precisa ser maior ou igual ao total da comanda;
  - pagamento com valor zero nao e aceito;
  - comanda fechada nao pode receber novos itens;
  - `payment_method` consolidado fica como `dinheiro + pix`, por exemplo.
- Pre-conta:
  - passa a listar as formas de pagamento quando a comanda ja estiver fechada.
- UI local:
  - fechamento aceita entrada no formato:
    - `dinheiro=30,pix=40`

### Aplicado no cliente instalado
- Backup:
  - `C:\MoviSyncAgent\backup_split_payments_20260502_222529`
- Arquivos atualizados:
  - `C:\MoviSyncAgent\agent_local\local_api.py`
  - `C:\MoviSyncAgent\agent_local\orders\*.py`
- API local reiniciada:
  - `http://127.0.0.1:8765`

### Validacao real no instalado
- Criada e fechada comanda teste:
  - `command_number=TESTE-PAG-DIV`
  - `uuid=4f419aff-e111-4cc0-8249-e33b4dacd967`
  - total `16.00`
  - pagamentos:
    - `dinheiro=6.00`
    - `pix=10.00`
  - status final `closed`
  - `payment_method=dinheiro + pix`
  - `amount_paid=16.00`
  - pre-conta validada com dinheiro + pix
- Status final:
  - `GET /status` -> `sync_running=true`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `14 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Proximo passo recomendado
1. Implementar impressao termica local.
2. Se houver cozinha/bar, separar impressao de producao por familia/impressora.
3. Depois avaliar se comanda fechada precisa virar pre-venda/orcamento no XD.

## Checkpoint preco automatico de produtos nas comandas - 2026-05-02

### Problema
- Produtos do catalogo local estavam vindo do XD com `unit_price=0`.
- Causa:
  - detector procurava campos genericos como `SalePrice`, `UnitPrice`, `Price`, `Pvp`;
  - tabela real `items` usa `RetailPrice1`;
  - `salesdocumentsreportview` usa `RetailPrice`.

### Correcao aplicada
- `agent_local/db/mariadb_client.py` agora prioriza:
  - `RetailPrice1`
  - `RetailPrice`
  - `SalePrice`
  - `UnitPrice`
  - `Price`
  - `Pvp`
  - `NetPrice1`
  - `AskingPrice`
- Fallback por historico de venda tambem usa `RetailPrice` quando disponivel.

### Aplicado no cliente instalado
- Backup:
  - `C:\MoviSyncAgent\backup_price_catalog_20260502_220714`
- Arquivo atualizado:
  - `C:\MoviSyncAgent\agent_local\db\mariadb_client.py`
- API local reiniciada:
  - `http://127.0.0.1:8765`

### Validacao real no instalado
- `GET /health` -> `{"status":"ok"}`
- `GET /orders/products?family=BEBIDAS` retornou precos reais:
  - `AGUA = 8.000000`
  - `COCA COLA 350ml = 8.000000`
  - `SUCO LARANJA = 14.000000`
- Criada e cancelada comanda teste:
  - `command_number=TESTE-PRECO-CODEX`
  - `uuid=f5378239-0fd0-4ec4-9d9b-644c66d4f95c`
  - item `AGUA`
  - quantidade `2`
  - preco unitario `8.000000`
  - total `16.00`
  - status final `cancelled`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `13 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Proximo passo recomendado
1. Validar manualmente na tela se todos os grupos principais trazem preco.
2. Implementar pagamento dividido.
3. Implementar impressao termica local, se houver impressora definida.

## Checkpoint operacao de comanda aberta - 2026-05-02

### Implementado
- Edicao de comanda aberta:
  - `POST /orders/{uuid}/items`
  - `PATCH /orders/{uuid}/items/{item_id}`
  - `DELETE /orders/{uuid}/items/{item_id}`
- Fechamento local:
  - `POST /orders/{uuid}/close`
  - salva `payment_method`, `amount_paid`, `closed_at`
  - bloqueia fechamento com valor pago menor que o total.
- Cancelamento local:
  - `POST /orders/{uuid}/cancel`
  - salva `cancel_reason`.
- Bloqueio operacional:
  - comanda `closed` ou `cancelled` nao aceita novo item, alteracao ou remocao.
- Recalculo de total:
  - total recalculado no servidor local apos adicionar, alterar ou remover item.
- UI local atualizada:
  - seleciona comanda aberta;
  - adiciona item na comanda selecionada;
  - altera quantidade/observacao por item;
  - remove item;
  - fecha comanda;
  - cancela comanda;
  - imprime pre-conta.

### Aplicado no cliente instalado
- Backup:
  - `C:\MoviSyncAgent\backup_comanda_ops_20260502_203914`
- Arquivos atualizados:
  - `C:\MoviSyncAgent\agent_local\local_api.py`
  - `C:\MoviSyncAgent\agent_local\db\mariadb_client.py`
  - `C:\MoviSyncAgent\agent_local\orders\*.py`
- API local reiniciada em:
  - `http://127.0.0.1:8765`

### Validacao real no instalado
- Criada comanda teste:
  - `command_number=TESTE-CODEX`
  - `table_reference=999`
  - `uuid=4ba4bd73-ed6f-49c1-b0cd-7489ae4b4bc6`
- Fluxo validado:
  - criar comanda -> `status=draft`
  - adicionar item -> total `5.00`
  - alterar quantidade/observacao -> total `7.00`
  - pre-conta -> `prebill=ok`
  - cancelar comanda -> `status=cancelled`
- Status final:
  - `GET /status` -> `sync_running=true`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `12 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Proximo passo recomendado
1. Testar manualmente a tela com uma comanda real curta.
2. Melhorar preco automatico dos produtos, pois alguns itens do XD ainda retornam `unit_price=0`.
3. Adicionar fluxo de pagamento com multiplas formas se o restaurante usar pagamento dividido.
4. Adicionar impressao em impressora termica local se necessario.

## Checkpoint comandas locais para restaurante - 2026-05-02

### Decisao tecnica
- A API de comandas continua somente local.
- Nao depende de licenca.
- Nao cria endpoint online.
- Nao mistura com relatorios centrais.
- Mesa e apenas referencia.
- Comanda e a entidade operacional principal.

### Implementado
- Abertura de comanda com:
  - `command_number`
  - `table_reference`
  - `operator_code`
  - `operator_name`
  - `status`
  - itens proprios
  - total proprio
- Permite mais de uma comanda na mesma mesa:
  - exemplo: mesa `10` pode ter comandas `001`, `002`, `003`.
- Operadores:
  - `GET /orders/operators`
  - busca automatica no banco XD quando `AGENT_MARIADB_URL` estiver configurado;
  - cache local em `local_order_operators`;
  - fallback local se XD estiver indisponivel.
- Familias/produtos:
  - `GET /orders/product-families`
  - `GET /orders/products?family=...`
  - busca automatica no banco XD quando possivel;
  - cache local em `local_order_products`;
  - tela exibe familias em carrossel e produtos por familia.
- Observacao por item:
  - campo `notes` em `local_order_items`.
- Pre-conta:
  - `GET /orders/{uuid}/prebill`
  - HTML imprimivel com botao de impressao.
  - inclui comanda, mesa, operador, itens, quantidades, valores, subtotal, total e observacoes.
- Tela local:
  - `http://127.0.0.1:8765/orders/ui`
  - titulo `Comandas Locais`
  - fluxo touch/balcao com seletor de operador, comanda, mesa, carrossel de familias e lista de produtos.

### Aplicado no cliente instalado
- Backup:
  - `C:\MoviSyncAgent\backup_comandas_20260502_193835`
- Arquivos atualizados:
  - `C:\MoviSyncAgent\agent_local\local_api.py`
  - `C:\MoviSyncAgent\agent_local\db\mariadb_client.py`
  - `C:\MoviSyncAgent\agent_local\orders\*.py`
- API local reiniciada em:
  - `http://127.0.0.1:8765`

### Validacao no instalado
- `GET /health` -> `{"status":"ok"}`
- `GET /orders/ui` -> `orders-ui=ok`
- `GET /orders/operators` retornou operadores reais:
  - `ADM`
  - `LAY`
  - `LUCIANO`
  - `MARIA`
  - `SUPORTE`
  - `TAINARA`
- `GET /orders/product-families` retornou familias reais:
  - `ALCOOLICOS`
  - `BEBIDAS`
  - `BIFUM`
  - `CARE`
  - `DIVERSOS`
  - `ENTRADAS`
  - `FRIOS`
  - `LAMEN`
  - `SOBA`
  - `SOBREMESA`
  - `SUSHI`
  - `TEISHOKU`
  - `UDON`
  - `YAKISOBA`
- `GET /orders/products?family=BEBIDAS` retornou produtos reais.
- `GET /status` -> `sync_running=true`
- Banco local de comandas:
  - `C:\MoviSyncAgent\agent_local\data\local_orders.db`

### Validacao no workspace
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_sales_mapping.py tests\test_source_connectors.py -q` -> `11 passed`
- `py -3 -m compileall agent_local -q` -> sem erro

### Limites atuais
- Ainda nao grava comanda no banco XD.
- Ainda nao baixa estoque.
- Ainda nao tem fechamento/pagamento.
- Alguns produtos podem vir com `unit_price=0` quando a tabela XD de produtos nao expuser preco direto; a tela permite editar o valor antes de salvar.

### Proximo passo recomendado
1. Validar criacao real de uma comanda teste na tela local.
2. Implementar edicao de comanda aberta:
   - adicionar item;
   - remover item;
   - alterar quantidade;
   - cancelar comanda.
3. Implementar fechamento/pagamento local.
4. Definir se a comanda sera apenas local ou se futuramente entra como pre-venda/orcamento no XD.

## Checkpoint pedidos locais offline iniciados - 2026-05-02

### Decisao tecnica
- Pedidos ficam somente locais nesta etapa.
- Nao foi criada API online de pedidos.
- Relatorios web centrais continuam separados.
- A nova frente usa a API local do agente em `http://127.0.0.1:8765`.

### Implementado
- Novo modulo local:
  - `agent_local/orders/`
- Storage local:
  - SQLite em `agent_local/data/local_orders.db`
  - configuravel por `LOCAL_ORDER_DB_PATH`
- Rotas locais:
  - `POST /orders`
  - `GET /orders`
  - `GET /orders/ui`
- Tela web local:
  - `http://127.0.0.1:8765/orders/ui`
- Seguranca local:
  - usa `X-Local-Token` quando existir token em `LOCAL_API_TOKEN_FILE`
  - default: `agent_local/data/local_api_token.txt`
- Pedido criado com:
  - `uuid`
  - `empresa_id`
  - `status=draft`
  - `sync_status=pending`
  - total calculado no servidor local
  - itens separados
  - registro em `local_order_outbox`
- Atalho operacional:
  - `scripts/open-local-orders.ps1`

### Validacao executada
- `py -3 -m pytest tests\test_agent_local_orders.py -q` -> `2 passed`
- `py -3 -m compileall agent_local -q` -> sem erro
- Aplicado tambem no agente instalado:
  - backup: `C:\MoviSyncAgent\backup_local_orders_20260502_190924`
  - arquivos copiados para `C:\MoviSyncAgent\agent_local\orders`
  - `C:\MoviSyncAgent\agent_local\local_api.py` atualizado
  - atalho criado: `C:\MoviSyncAgent\Abrir_Pedidos_Locais.cmd`
- Validacao no instalado:
  - `GET http://127.0.0.1:8765/health` -> `{"status":"ok"}`
  - `GET http://127.0.0.1:8765/orders/ui` -> tela carregada
  - `GET http://127.0.0.1:8765/orders` com `X-Local-Token` -> `{"total":0,"orders":[]}`
  - banco local criado: `C:\MoviSyncAgent\agent_local\data\local_orders.db`
  - `GET http://127.0.0.1:8765/status` -> `sync_running=true`

### Limite atual
- Ainda nao grava pedido no XD.
- Ainda nao sincroniza pedido para o servidor.
- Ainda nao tem login local por usuario.
- Ainda nao tem edicao/cancelamento/status do pedido.

### Proximo passo recomendado
1. Abrir `C:\MoviSyncAgent\Abrir_Pedidos_Locais.cmd` ou `http://127.0.0.1:8765/orders/ui`.
2. Informar o token local no campo da tela se a API exigir autenticacao.
3. Criar pedido teste local.
4. Depois evoluir status, usuario local e impressao/retirada.

## Checkpoint reprocessamento historico concluido - 2026-05-02

### Estado atual validado
- Branch local atual:
  - `main`
- Git local:
  - limpo antes da atualizacao deste checkpoint.
- Producao:
  - `https://movisystecnologia.com.br/healthz` -> `ok`
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `ready`
- Agente instalado:
  - caminho real: `C:\MoviSyncAgent`
  - API local ativa em `http://127.0.0.1:8765/status`
  - `sync_running=true`
  - checkpoint instalado final:
    - `12345678000199:vendas = 2026-03-28T15:36:02+00:00`

### Reprocessamento executado
- Ambiente usado:
  - `C:\MoviSyncAgent`
  - `C:\MoviSyncAgent\.venv\Scripts\python.exe`
- Backup criado antes do reset:
  - `C:\MoviSyncAgent\backup_reprocess_20260502_113800\checkpoints.before_reprocess.json`
- Checkpoint instalado resetado para:
  - `12345678000199:vendas = 1970-01-01T00:00:00+00:00`
- Lotes executados ate zerar:
  - total aproximado processado: `48901` vendas
  - ultimo lote util: `processed_count=63`
  - lote final: `processed_count=0`
- Sync normal religado depois do reprocessamento.
- Status final local:
  - `curl.exe -sS http://127.0.0.1:8765/status`
  - retorno validado:
    - `status=running`
    - `sync_running=true`

### Observacao tecnica
- O `start_agent()`/runtime instalado sobe mais de um PID `agent_local.main`.
- O criterio operacional validado foi o status oficial da API local:
  - `sync_running=true`
- Nao foi feita alteracao de codigo nesta etapa.

### Proximo ponto exato
1. Validar visualmente os relatorios em producao:
   - `Hoje`
   - `Mes`
   - `Semestre`
   - `Ano`
   - detalhe por forma de pagamento
   - faturamento total
   - exportacoes PDF/Excel/CSV no mesmo periodo.
2. Se os totais ainda parecerem incorretos, investigar dado fonte no servidor por `empresa_id`, `uuid`, `data`, `data_atualizacao` e `forma_pagamento`, sem alterar novamente o mapper antes dessa prova.

## Checkpoint relatorios por periodo e reprocessamento pendente - 2026-05-02

### Estado atual validado
- Branch local atual:
  - `main`
- Git local:
  - limpo no final da sessao.
- Producao:
  - ultimo deploy validado com sucesso.
  - `https://movisystecnologia.com.br/healthz` -> `ok`
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `ready`
- Agente instalado:
  - caminho real: `C:\MoviSyncAgent`
  - API local ativa em `http://127.0.0.1:8765/status`
  - status validado apos religar:
    - `sync_running=true`
    - processos `agent_local.main` ativos como `pythonw.exe`
    - tray ativo como `pythonw.exe`
- Nao ficou processo extra de reprocessamento rodando.

### Problema reportado
- Ao selecionar periodos pre-definidos (`Hoje`, `Mes`, `Semestre`, `Ano`), os relatorios ainda pareciam puxar tudo.
- O problema aparecia tanto nos cards de total/faturamento quanto no detalhe agrupado, por exemplo `Forma de pagamento`.
- Na tela, o preset `Semestre` aparecia selecionado, mas o total exibido continuava muito alto.

### Diagnostico tecnico
- Primeiro problema encontrado:
  - `start_date` e `end_date` antigos continuavam sendo enviados pelo formulario;
  - o backend priorizava essas datas antigas e ignorava o preset.
- Correcao feita no PR `#53`:
  - `Hoje`, `Mes`, `Semestre`, `Ano` agora prevalecem sobre datas manuais;
  - datas manuais so valem quando `period_preset=custom`;
  - frontend limpa/desabilita datas quando o periodo selecionado nao e `Personalizado`;
  - ao editar data manual, o preset volta para `Personalizado`.
- Segundo problema encontrado:
  - a query do agente local estava usando `CreationDate` como `data` do relatorio;
  - na base XD real, isso pode colocar muitas vendas antigas dentro do mesmo periodo, fazendo parecer que o filtro por periodo nao funciona;
  - o filtro SQL central ja usa `Venda.data`, entao o problema era a data gravada em `Venda.data`, nao o WHERE dos relatorios.
- Correcao feita no PR `#54`:
  - `agent_local/db/xd_sales_mapper.py` passou a usar `CloseDate` como data da venda nos relatorios;
  - fallback permanece em `CreationDate`;
  - `data_atualizacao` continua usando `CloseDate` com fallback em `CreationDate`.

### PRs recentes desta etapa
- PR `#49`:
  - `Show report growth value in KPI`
  - KPI crescimento deixou de mostrar apenas `Novo`.
- PR `#50`:
  - `Show report growth amount and percent`
  - Crescimento passou a mostrar valor e percentual.
  - Cor de `Nao informado` no grafico circular passou a preto.
- PR `#51`:
  - `Fix report drilldown selection`
  - Clique em produto/familia/pagamento/terminal passou a aplicar filtro real.
- PR `#52`:
  - `Show daily revenue KPI summary`
  - Aba `Faturamento do Dia` passou a mostrar faturamento total, total de vendas e crescimento.
  - API de KPIs passou a devolver tambem `kpi_cards`.
- PR `#53`:
  - `Fix report period preset filters`
  - Presets de periodo passaram a prevalecer sobre datas antigas.
- PR `#54`:
  - `Use sale close date for report periods`
  - Agente passou a gravar data de relatorio usando `CloseDate`.

### Validacoes executadas nesta etapa
- Para PR `#53`:
  - `py -3 -m pytest tests\test_sync_admin_report_ui.py -q` -> `8 passed`
  - `py -3 -m pytest tests\test_sync_admin_rbac.py::test_report_period_is_limited_to_fourteen_months tests\test_sync_admin_rbac.py::test_report_period_presets_override_manual_dates -q` -> `2 passed`
  - `py -3 -m compileall sync-admin\app -q` -> sem erro
- Para PR `#54`:
  - `py -3 -m pytest tests\test_agent_local_sales_mapping.py -q` -> `6 passed`
  - `py -3 -m pytest tests\test_sync_upsert.py -q` -> `5 passed`
  - `py -3 -m pytest tests\test_sync_admin_report_ui.py tests\test_sync_admin_rbac.py::test_report_period_presets_override_manual_dates -q` -> `9 passed`
  - `py -3 -m compileall agent_local backend sync-admin\app -q` -> sem erro

### Alteracao aplicada no cliente instalado
- Arquivo copiado manualmente do workspace para o agente instalado:
  - origem: `E:\Projetos\INTEGRADO_WEB_XD\agent_local\db\xd_sales_mapper.py`
  - destino: `C:\MoviSyncAgent\agent_local\db\xd_sales_mapper.py`
- Sync local foi religado com:
  - `C:\MoviSyncAgent\.venv\Scripts\python.exe -c "from agent_local.tray_app import start_agent; print(start_agent())"`
- Estado final validado:
  - `curl.exe -sS http://127.0.0.1:8765/status`
  - retorno esperado:
    - `sync_running=true`

### Reprocessamento antigo ficou incompleto
- Foi iniciado reprocessamento para reenviar vendas antigas com a data corrigida.
- Passos executados:
  - processos `agent_local.main` do instalado foram parados;
  - checkpoint local do workspace foi resetado:
    - `py -3 -m agent_local.sync.reset_checkpoint --since 1970-01-01T00:00:00+00:00 --confirm`
  - o reprocessamento com `py -3 -m agent_local.sync.run_once` foi iniciado em loop.
- O usuario interrompeu a execucao antes de terminar.
- Resultado:
  - reprocessamento ficou parcial;
  - checkpoint chegou a:
    - `12345678000199:vendas = 2025-10-19T13:00:17+00:00`
  - processo extra foi parado depois;
  - sync normal foi religado.
- O arquivo `agent_local/data/checkpoints.json` do workspace foi restaurado no git para nao deixar sujeira local.

### Ponto exato para continuar depois
1. Confirmar estado atual:
   ```powershell
   curl.exe -sS http://127.0.0.1:8765/status
   git status --short --branch
   ```
2. Se for corrigir os dados historicos ja enviados, parar o sync normal do instalado antes:
   ```powershell
   Get-CimInstance Win32_Process |
     Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -like '*C:\MoviSyncAgent*' -and $_.CommandLine -like '*agent_local.main*' } |
     ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
3. Resetar checkpoint no ambiente correto.
   - Se for usar o workspace:
     ```powershell
     py -3 -m agent_local.sync.reset_checkpoint --since 1970-01-01T00:00:00+00:00 --confirm
     ```
   - Se for usar o instalado, rodar em `C:\MoviSyncAgent` com a venv do instalado.
4. Reprocessar ate `processed_count=0`.
   - Nao interromper no meio.
   - Rodar lotes repetidos de:
     ```powershell
     py -3 -m agent_local.sync.run_once
     ```
5. Depois religar sync normal:
   ```powershell
   C:\MoviSyncAgent\.venv\Scripts\python.exe -c "from agent_local.tray_app import start_agent; print(start_agent())"
   ```
6. Validar relatorios:
   - `Hoje`
   - `Mes`
   - `Semestre`
   - `Ano`
   - detalhes por forma de pagamento
   - faturamento total
   - PDF/Excel/CSV com o mesmo periodo.

### Observacao importante
- PR `#54` corrige os proximos envios.
- Para os relatorios historicos ficarem certos, os registros antigos no servidor precisam ser reenviados com a nova data.
- Sem reprocessamento completo, parte dos dados antigos pode continuar aparecendo fora do periodo esperado.

## Checkpoint data de criacao das vendas no agente local - 2026-05-01

### Problema operacional
- O agente local estava usando `CloseDate` como data principal da venda quando esse campo existia.
- Isso podia fazer relatorios por data seguirem a data de fechamento/atualizacao, nao a data de criacao da venda no banco local.

### Correcao aplicada
- Em `salesdocumentsreportview`:
  - `data` agora usa `DATE(COALESCE(v.CreationDate, v.CloseDate))`;
  - `data_atualizacao` continua usando `COALESCE(v.CloseDate, v.CreationDate)`.
- No fallback `Documentsbodys/Documentsheaders`:
  - `data` prioriza `CreationDate`;
  - `data_atualizacao` prioriza `CloseDate`.
- Motivo tecnico:
  - relatorios devem obedecer a data de criacao da venda;
  - checkpoint incremental deve continuar usando data de fechamento/atualizacao para nao perder alteracoes posteriores.

### Atualizacao aplicada no cliente instalado
- Arquivo atualizado:
  - `C:\MoviSyncAgent\agent_local\db\xd_sales_mapper.py`
- Sync reiniciado pelo autostart:
  - `http://127.0.0.1:8765/status` -> `sync_running=true`

### Validacao local
- `py -3 -m pytest tests\test_agent_local_sales_mapping.py tests\test_agent_checkpoint_reset.py -q` -> `8 passed`.
- `py -3 -m compileall agent_local -q` -> sem erro.

### Proximo ponto de retomada
1. Reprocessar vendas antigas se precisar corrigir datas ja enviadas antes desta alteracao.
2. Para reprocessar por empresa:
   - resetar checkpoint do agente local;
   - executar sync em lotes;
   - validar relatorios por periodo.

## Checkpoint relatorios filtrados e exportacao fiel - 2026-05-01

### Problema operacional
- A tela de relatorios mostrava filtros como campos livres.
- Familia, categoria, pagamento, bandeira, cliente, operador, terminal e produto nao vinham como opcoes reais do banco.
- Exportacoes podiam sair com outra visao, porque CSV, Excel e PDF usavam estruturas genericas em vez do resultado do relatorio selecionado.
- Categoria usava busca ampla em produto/familia/codigo, gerando risco de misturar dados fora do filtro selecionado.

### Correcao aplicada
- Criado endpoint backend:
  - `GET /admin/tenants/{empresa_id}/reports/filter-options`
- As opcoes agora saem dinamicamente da tabela `vendas`, sempre por `empresa_id`.
- Filtros dinamicos cobertos:
  - produto;
  - codigo local;
  - familia;
  - categoria;
  - forma de pagamento;
  - bandeira;
  - cliente;
  - operador;
  - terminal;
  - status.
- Filtros de familia, categoria, produto, bandeira, cliente e operador passaram a respeitar valor selecionado.
- Forma de pagamento tambem trata labels compostas por virgula, sem precisar de opcoes fixas.
- Relatorios novos no portal:
  - por categoria;
  - por bandeira;
  - por operador;
  - por cliente.
- Exportacao agora usa a tabela do `report_view` selecionado:
  - PDF;
  - Excel;
  - CSV.
- Exportacao inclui total geral:
  - quantidade total;
  - valor bruto total;
  - desconto total;
  - acrescimo total;
  - valor final total.

### Arquivos alterados
- `backend/api/routes/tenant_admin.py`
- `backend/repositories/venda_repository.py`
- `backend/schemas/tenant_reports.py`
- `backend/services/tenant_report_service.py`
- `sync-admin/app/services/control_service.py`
- `sync-admin/app/services/export_service.py`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `sync-admin/app/web/routes/pages.py`
- `tests/test_sync_admin_rbac.py`
- `tests/test_sync_upsert.py`

### Validacao local
- `py -3 -m compileall backend sync-admin\app -q` -> sem erro.
- `py -3 -m pytest tests\test_sync_upsert.py tests\test_sync_admin_rbac.py tests\test_sync_admin_report_ui.py -q` -> `21 passed`.
- `py -3 -m pytest tests\test_api_integration.py tests\test_release_smoke_contract.py -q` -> `2 passed, 1 skipped`.
- A suite completa `py -3 -m pytest -q` excedeu 5 minutos e foi interrompida por timeout do ambiente.
- O timeout deixou lock temporario em `output/test_sync_admin_rbac.db`; o arquivo foi removido e os testes focados passaram.

### Proximo ponto de retomada
1. Validar visualmente `/client/reports` em producao com:
   - pagamento `PIX`;
   - produto + periodo;
   - operador;
   - categoria;
   - bandeira.
2. Baixar PDF, Excel e CSV para cada visao e comparar com a tabela exibida.
3. Se algum campo vier vazio, verificar se o agente local esta recebendo esse campo da base XD antes de mexer na tela.

## Checkpoint instalador cliente, tray e sync oculto - 2026-05-01

### Problema operacional
- O instalador precisava ficar simples para usuario leigo.
- O sincronizador precisava mostrar estado perto do relogio.
- O usuario precisava iniciar, parar e reiniciar o sync pelo icone.
- A tela preta ainda aparecia ao ativar o Sync.
- O botao `Painel Local` nao abria de forma confiavel quando chamado por atalho/menu.

### Correcao aplicada
- Criado instalador guiado com ponto de entrada:
  - `infra/client-agent/COMECE_AQUI.bat`
- Atualizado instalador:
  - `infra/client-agent/install-agent-client.ps1`
  - `infra/client-agent/Setup_Instalar_Cliente.bat`
- Criado icone de bandeja do Windows:
  - `agent_local/tray_app.py`
- Menu do icone:
  - iniciar sincronizacao;
  - parar sincronizacao;
  - reiniciar sincronizacao;
  - abrir Painel Local;
  - abrir log.
- Atalhos do Desktop agora apontam para `.vbs`, nao para `.cmd`.
- Painel Local abre por:
  - `Abrir_Painel_Local.vbs`
  - `pythonw.exe -m agent_local.pairing_ui`
- Status/icone abre por:
  - `Abrir_Status_Sync.vbs`
  - `pythonw.exe -m agent_local.tray_app`
- Sync oculto abre por:
  - `Iniciar_Agente.vbs`
  - `pythonw.exe -m agent_local.main`
- O tray tambem passou a iniciar o sync com `pythonw.exe`.
- O menu `Abrir painel local` prioriza `.vbs` e so usa `.cmd` como fallback.

### Instalador renovado
- Release atual:
  - `infra/client-agent/releases/v2026-05-01_tray`
- ZIP atual:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_tray.zip`
- Tamanho validado:
  - `128411` bytes
- Data local do ZIP:
  - `2026-05-01 01:05:41`

### Atualizacao aplicada no cliente instalado
- Instalacao real atualizada em:
  - `C:\MoviSyncAgent`
- Arquivos atualizados no instalado:
  - `C:\MoviSyncAgent\agent_local\tray_app.py`
  - `C:\MoviSyncAgent\Abrir_Painel_Local.vbs`
  - `C:\MoviSyncAgent\Abrir_Status_Sync.vbs`
  - `C:\MoviSyncAgent\Iniciar_Agente.vbs`
- Processo validado apos reinicio:
  - `agent_local.tray_app` rodando como `pythonw.exe`
  - `agent_local.main` rodando como `pythonw.exe`
- Nao havia mais `python.exe` do MoviSync depois do hotfix.

### Validacao local
- `install-agent-client.ps1` parse OK.
- `py -3 -m compileall infra\client-agent\releases\v2026-05-01_tray\agent_local infra\client-agent\releases\v2026-05-01_tray\backend -q` -> sem erro.
- Atalhos do Desktop validados:
  - `MoviSync Painel Local.lnk` -> `C:\MoviSyncAgent\Abrir_Painel_Local.vbs`
  - `MoviSync Status do Sync.lnk` -> `C:\MoviSyncAgent\Abrir_Status_Sync.vbs`
  - `MoviSync Iniciar Agente.lnk` -> `C:\MoviSyncAgent\Abrir_Status_Sync.vbs`

### Git, PRs e deploy
- PR `#35`:
  - `Add guided client installer flow`
  - deploy `25198835361` -> `success`
- PR `#36`:
  - `Add Windows tray sync controls`
  - deploy `25199325790` -> `success`
- PR `#37`:
  - `Fix client tray launch shortcuts`
  - deploy `25201374952` -> `success`
- PR `#38`:
  - `Hide sync activation console`
  - deploy `25201493023` -> `success`

### Producao validada apos ultimo deploy
- `https://movisystecnologia.com.br/healthz` -> `ok`
- `https://movisystecnologia.com.br/readyz/backend` -> `ready`
- `https://movisystecnologia.com.br/admin/api/health/ready` -> `ready`

### Proximo ponto de retomada
1. Se o usuario ainda vir tela preta, verificar se ela vem de `Iniciar_Agente_Debug.cmd` ou de processo antigo aberto manualmente.
2. Para nova instalacao em cliente, usar:
   - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_tray.zip`
3. Para atualizar cliente ja instalado, substituir:
   - `agent_local/tray_app.py`
   - `Abrir_Painel_Local.vbs`
   - `Abrir_Status_Sync.vbs`
   - `Iniciar_Agente.vbs`
4. Confirmar processos com:
   - `Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('python.exe','pythonw.exe')) -and $_.CommandLine -like '*C:\MoviSyncAgent*' }`
5. Estado esperado:
   - somente `pythonw.exe` para `agent_local.tray_app`
   - somente `pythonw.exe` para `agent_local.main`

### Hotfix API local no Windows - 2026-05-01
- Problema reportado:
  - API Sync local nao subia junto com o Windows.
- Correcao aplicada:
  - criado `agent_local/local_api.py`;
  - criado `agent_local/windows_autostart.py`;
  - instalador cria `Abrir_API_Local.vbs`;
  - instalador cria `Iniciar_MoviSync_Windows.vbs`;
  - instalador cria `MoviSync AutoStart.lnk` na pasta Startup do usuario.
- API local:
  - `GET http://127.0.0.1:8765/health`;
  - `GET http://127.0.0.1:8765/status`;
  - `POST http://127.0.0.1:8765/sync/start`;
  - `POST http://127.0.0.1:8765/sync/stop`;
  - `POST http://127.0.0.1:8765/sync/restart`.
- Seguranca:
  - API escuta somente em `127.0.0.1`;
  - comandos POST usam `X-Local-Token` quando existe `agent_local/data/local_api_token.txt`.
- Atualizacao aplicada no instalado:
  - `C:\MoviSyncAgent\agent_local\local_api.py`;
  - `C:\MoviSyncAgent\agent_local\windows_autostart.py`;
  - `C:\MoviSyncAgent\Abrir_API_Local.vbs`;
  - `C:\MoviSyncAgent\Iniciar_MoviSync_Windows.vbs`;
  - `C:\Users\Rodrigo Tejada\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\MoviSync AutoStart.lnk`.
- Dependencias instaladas no venv real:
  - `fastapi==0.115.12`;
  - `uvicorn==0.30.6`.
- Validacao real:
  - `curl http://127.0.0.1:8765/health` -> `{"status":"ok"}`;
  - `curl http://127.0.0.1:8765/status` -> `sync_running=true`;
  - processos `agent_local.local_api`, `agent_local.tray_app` e `agent_local.main` ativos.
- Instalador renovado:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_tray.zip`;
  - tamanho `130754` bytes;
  - data local `2026-05-01 16:10:56`.

## Checkpoint status do agente local em relatorios - 2026-04-30

### Problema operacional
- A validacao visual de `/client/reports` exige sessao autenticada.
- A senha administrativa antiga documentada (`admin/admin123`) nao autenticou em producao.
- O `ADMIN_TOKEN` local em `.env.prod` tambem nao correspondeu ao token ativo em producao.
- SSH direto para `root@172.238.213.72` falhou com `Permission denied (publickey)`.
- Pela analise do codigo, o KPI `Status da sincronizacao` depende de `local_clients.last_sync_at`.
- O agente local real sincronizava vendas via `/sync`, mas nao enviava heartbeat de status quando um ciclo terminava.
- Resultado: o relatorio podia mostrar `Sem sync` mesmo depois de o agente ter concluido catch-up de vendas.

### Correcao aplicada localmente
- Criado endpoint autenticado por tenant:
  - `POST /sync/status`
- O endpoint usa `X-Empresa-Id` + `X-API-Key`.
- O endpoint aceita `X-Agent-Device-Label` para identificar o agente local sem expor segredo.
- O backend atualiza `local_clients.last_sync_at`, `last_seen_at`, `status` e `last_status_json`.
- O agente local passou a enviar status em todo ciclo:
  - quando envia lote de vendas;
  - quando nao ha registros novos.
- O envio de status e tolerante a falhas:
  - falha no heartbeat nao bloqueia o envio de vendas;
  - o erro fica em log como `sync_status_update_failed`.

### Arquivos alterados
- `backend/api/routes/sync.py`
- `backend/repositories/local_client_repository.py`
- `backend/schemas/sync.py`
- `agent_local/sync/api_client.py`
- `agent_local/sync/sync_runner.py`
- `agent_local/main.py`
- `agent_local/sync/run_once.py`
- `tests/test_sync_status_reporting.py`

### Validacao local
- `py -3 -m compileall backend agent_local -q` -> sem erro.
- `py -3 -m pytest tests\test_sync_status_reporting.py -q` -> `2 passed`.
- `py -3 -m pytest tests\test_sync_status_reporting.py tests\test_api_integration.py tests\test_sync_admin_report_ui.py -q` -> `7 passed`.
- `py -3 -m pytest tests\test_agent_checkpoint_reset.py tests\test_agent_local_sales_mapping.py -q` -> `7 passed`.
- `py -3 -m pytest -q` -> `61 passed, 1 skipped`.

### Proximo passo seguro
1. Validar visualmente se o relatorio troca `Sem sync` por data real.
2. Conferir uma amostra do unico registro ainda sem `familia_produto`.
3. Validar exportacoes PDF, Excel e CSV em producao com filtros combinados.

### Git, deploy e agente instalado
- Branch:
  - `codex/fix-agent-sync-status-heartbeat`
- PR:
  - `#32` - `Fix agent sync status heartbeat`
- Merge em `main`:
  - `ba4d98e` - `Fix agent sync status heartbeat`
- Deploy GitHub Actions:
  - run `25198198983`
  - status `success`
- Producao validada apos deploy:
  - `https://movisystecnologia.com.br/healthz` -> `ok`
  - `https://movisystecnologia.com.br/readyz/backend` -> `ready`
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `ready`
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `ready`
- Agente instalado atualizado em:
  - `C:\MoviSyncAgent`
- Backup dos arquivos antigos:
  - `C:\MoviSyncAgent\backup_status_heartbeat_20260430_225158`
- Ciclo unico executado:
  - `POST https://movisystecnologia.com.br/admin/api/sync/status` -> `200 OK`
  - retorno: `status=ok`, `empresa_id=12345678000199`, `client_id=492490b3-2b1a-5fa0-9962-4cf5a1130f9a`
  - `last_sync_at=2026-05-01T01:52:33.970303Z`
- Agente em background iniciado:
  - processo `python.exe` em `C:\MoviSyncAgent\.venv\Scripts\python.exe`
  - intervalo `SYNC_INTERVAL_MINUTES=15`
  - log confirmou novo ciclo com `POST /sync/status` -> `200 OK` em `2026-05-01T01:52:46Z`

## Checkpoint relatorios - grafico por pagamento e KPIs - 2026-04-30

### Problema operacional
- No portal de relatorios, o grafico pizza de pagamentos exibia muitas labels compostas e repetidas.
- Exemplos observados:
  - `Dinheiro, Rede Credito`
  - `Rede Credito, Rede Debito`
  - `Credito Cielo, VOUCHER`
- A legenda ficava poluida e parecia duplicada.
- O card `Crescimento` mostrava `0.0%` mesmo quando nao havia base comparativa.
- O card `Status da sincronizacao` mostrava `-`, dificultando diagnostico operacional.

### Correcao aplicada
- Criado tratamento no servidor web para consolidar pagamentos antes da renderizacao:
  - `sync-admin/app/web/routes/pages.py`
  - helper `_split_payment_label`
  - helper `_normalize_payment_breakdown_items`
- Labels compostas por virgula agora sao separadas por forma individual.
- Nomes repetidos no mesmo registro sao deduplicados.
- Valores de registros compostos sao alocados proporcionalmente entre as formas de pagamento.
- O payload de `payment_items`, `payment_chart_labels` e `payment_chart_values` agora sai consolidado por nome de pagamento.
- O JavaScript do grafico passou a limitar legenda de pizza quando houver mais de 8 itens:
  - `sync-admin/app/static/js/reports.js`
  - `data-legend-limit="8"` no parcial de relatorios.
- O KPI `Crescimento` agora mostra:
  - `Sem base` quando nao existe periodo anterior valido;
  - `Novo` quando o periodo anterior nao teve faturamento;
  - percentual real quando existe base comparativa.
- O KPI `Status da sincronizacao` agora mostra:
  - `Sem agente` quando nao ha API local conectada;
  - `Sem sync` quando existe cliente remoto sem data de sync;
  - ultima data quando disponivel.

### Arquivos alterados
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/static/js/reports.js`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `tests/test_sync_admin_report_ui.py`
- `docs/relatorios_comerciais_financeiros.md`

### Testes e validacao local
- `py -3 -m pytest tests\test_sync_admin_report_ui.py -q` -> `3 passed`.
- `py -3 -m pytest -q` -> `59 passed, 1 skipped`.
- `py -3 -m compileall sync-admin\app -q` -> sem erro.

### Git, PR e deploy
- Branch:
  - `codex/fix-report-payment-chart-status`
- PR:
  - `#30` - `Fix payment report chart and sync status KPIs`
- Merge commit em `main`:
  - `8a0cf2f` - `Fix payment report chart and sync status KPIs`
- Deploy GitHub Actions:
  - run `25148435212`
  - status `success`
- VPS:
  - `/opt/integrado_web_xd` em `8a0cf2f`
  - containers `integrado-backend`, `integrado-db`, `integrado-frontend`, `integrado-nginx` rodando e saudaveis.

### Validacao em producao
- Endpoints publicos OK:
  - `https://movisystecnologia.com.br/healthz` -> `ok`
  - `https://movisystecnologia.com.br/readyz/backend` -> `ready`
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `ready`
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `ready`
- Validacao do payload real para `empresa_id=12345678000199` e marco/2026:
  - labels consolidadas:
    - `Rede Credito`
    - `VOUCHER`
    - `Rede Debito`
    - `Dinheiro`
    - `Credito Cielo`
    - `PIX DEBITO`
    - `Debi Cielo`
  - `payment_count=7`
  - `Crescimento=-10.4%`
  - `Status da sincronizacao=Sem sync`

### Proximo passo seguro
1. Abrir visualmente `/client/reports?empresa_id=12345678000199&report_view=payments&period_preset=custom&start_date=2026-03-01&end_date=2026-03-31`.
2. Confirmar se o status `Sem sync` corresponde ao agente local ainda sem `last_sync_at` registrado no receptor remoto.
3. Se necessario, ajustar o agente local para enviar snapshot de status/sync em todos os ciclos.

## Checkpoint retomada operacional - reset seguro de vendas - 2026-04-29

### Problema operacional
- A correcao de `familia_produto` ja esta no `main` e em producao.
- Os registros antigos da empresa `12345678000199` continuam sem familia real porque foram sincronizados antes do agente local enviar esse campo.
- O agente local tinha apenas checkpoint JSON, sem comando seguro para reprocessar vendas antigas.

### Correcao aplicada localmente
- `agent_local/sync/checkpoint_store.py` ganhou metodo `reset`.
- Criado CLI:
  - `python -m agent_local.sync.reset_checkpoint`
- Criado CLI de ciclo unico:
  - `python -m agent_local.sync.run_once`
- O comando exige `--confirm` para gravar no checkpoint.
- O reset e por chave isolada:
  - `{empresa_id}:vendas`
- Nao altera API key, configuracao de banco, URL do servidor ou dados sincronizados.
- `agent_local/db/mariadb_client.py` agora trata `AGENT_SOURCE_QUERY` legado de `salesdocumentsreportview` sem campos canonicos como autodeteccao.
- `agent_local/db/xd_sales_mapper.py`:
  - converte `cancelada` para booleano;
  - filtra registros com `TotalAmount <= 0`, porque a API central exige `valor > 0`.
- `agent_local/sync/api_client.py` agora inclui corpo de erro HTTP na excecao para diagnostico de 422/400.
- `infra/client-agent/install-agent-client.ps1` atualiza `AGENT_SOURCE_QUERY` legado para `auto` e grava `.env` sem BOM.

### Comando operacional para reprocessar vendas
- Reprocessar tudo:
  - `py -3 -m agent_local.sync.reset_checkpoint --empresa-id 12345678000199 --checkpoint-file agent_local/data/checkpoints.json --confirm`
- Reprocessar a partir de uma data especifica:
  - `py -3 -m agent_local.sync.reset_checkpoint --empresa-id 12345678000199 --checkpoint-file agent_local/data/checkpoints.json --since 2026-04-01T00:00:00 --confirm`
- Depois do reset:
  - executar o agente local normalmente para reenviar os lotes;
  - como o backend usa UPSERT por `empresa_id + uuid`, o reenvio atualiza os registros existentes sem misturar tenants.

### Validacao local
- `py -3 -m pytest tests\test_agent_checkpoint_reset.py tests\test_agent_local_sales_mapping.py -q` -> `6 passed`.
- CLI validado com arquivo de checkpoint isolado em `output/test_agent_checkpoint_reset/cli_checkpoints.json`.
- Validacao apos hardening de mapper/client:
  - `py -3 -m pytest tests\test_agent_checkpoint_reset.py tests\test_agent_local_sales_mapping.py tests\test_sync_upsert.py -q` -> `12 passed`.

### Execucao real no agente instalado
- Instalacao real detectada:
  - `C:\MoviSyncAgent`
- Corrigido `.env` instalado:
  - `AGENT_SOURCE_QUERY=auto`
  - `.env` regravado sem BOM para `AGENT_EMPRESA_ID` carregar corretamente.
- Checkpoint real resetado:
  - `12345678000199:vendas=1970-01-01T00:00:00+00:00`
- Primeiro lote com `BATCH_SIZE=1`:
  - `updated_count=1`
- Lote 50:
  - `processed_count=50`
- Lotes seguintes executados com sucesso, incluindo lotes de 500 e 1000.
- Erros encontrados e corrigidos:
  - `422 valor > 0` causado por venda local com `TotalAmount=0`;
  - corrigido com filtro de origem `COALESCE(TotalAmount, 0) > 0`.
- Reprocessamento continuado em 2026-04-30 com lotes de ate 1000.
- Checkpoint real final:
  - `2026-03-28T15:36:02+00:00`
- Ultimo ciclo:
  - `processed_count=0`
- Intervalo do agente restaurado:
  - `SYNC_INTERVAL_MINUTES=15`
- Processo em background:
  - nao ha `python.exe` ativo em `C:\MoviSyncAgent` no momento deste registro.
- Validacao na VPS apos catch-up:
  - `total=48895`
  - `family_filled=48894`
  - `family_distinct=13`

### Proximo passo seguro
1. Validar visualmente `/client/reports?report_view=families` em producao.
2. Conferir uma amostra do unico registro ainda sem `familia_produto`.
3. Manter `SYNC_INTERVAL_MINUTES=15` no agente instalado.

## Checkpoint relatorios comerciais/financeiros - 2026-04-29

### Correcao familia em relatorios cliente - 2026-04-29

Problema validado em producao:

- URL afetada:
  - `/client/reports?empresa_id=12345678000199&report_view=families&period_preset=custom&top_limit=10&recent_limit=20`
- Diagnostico no PostgreSQL da VPS:
  - `total_rows=485`;
  - `family_not_null=0`;
  - `family_filled=0`;
  - amostras tambem sem `codigo_produto_local`.
- Causa:
  - dados existentes foram sincronizados sem `familia_produto` e sem `codigo_produto_local`;
  - o mapper XD precisava cobrir tambem o caminho `ItemKeyId -> Items.KeyId -> Items.GroupId -> Itemsgroups`.

Correcao aplicada:

- `agent_local/db/xd_sales_mapper.py` agora busca familia:
  - por `ItemGroupId` direto quando existir;
  - por `Items.GroupId` a partir de `ItemKeyId` quando a view/tabela de vendas nao trouxer `ItemGroupId`.
- `backend/repositories/venda_repository.py` trata familia vazia como `Nao informado` nos agrupamentos.
- Testes adicionados:
  - mapper XD com `Items + Itemsgroups`;
  - agrupamento de familia vazia.

Validacao local:

- `py -3 -m pytest tests\test_agent_local_sales_mapping.py tests\test_sync_upsert.py -q` -> `9 passed`.
- `py -3 -m pytest -q` -> `51 passed, 1 skipped`.

Git/VPS:

- PR:
  - `#25` - `Fix XD product family mapping in reports`.
- Commit em `main`:
  - `b3fb936` - `fix: map XD product families through items (#25)`.
- Deploy VPS:
  - `/opt/integrado_web_xd` em `b3fb936`;
  - `bash infra/scripts/deploy-prod.sh` executado com sucesso;
  - migration sem pendencias: `current_version=6`;
  - containers `integrado-backend`, `integrado-frontend`, `integrado-nginx` healthy.
- Pos-deploy:
  - `infra/nginx/default.conf` foi restaurado para a versao Git e recarregado com `nginx -s reload`;
  - HTTPS validado por GET a partir da VPS:
    - `/healthz` -> `200`;
    - `/readyz/backend` -> `200`;
    - `/readyz/sync-admin` -> `200`;
    - `/admin/api/health/ready` -> `200`.
- API interna validada:
  - `/admin/tenants/12345678000199/reports/breakdown?group_by=familia_produto&limit=10` -> `200`;
  - retorno atual: `Nao informado`, `total_records=485`, `total_sales_value=20132.21`.

Ponto operacional:

- Para a empresa `12345678000199`, a producao so passara a mostrar familias reais depois de atualizar o agente local e reenviar/reprocessar as vendas do periodo, porque os registros atuais no banco central nao possuem a informacao.

### Entrega local
- Modulo de relatorios ampliado para BI comercial/financeiro:
  - filtros por produto, codigo local, familia, forma de pagamento, bandeira, operador, cliente, cancelamento e status;
  - agrupamentos adicionais por pagamento, bandeira, familia, categoria, terminal, filial, operador, cliente, status e codigo local;
  - totais detalhados: bruto, descontos, acrescimos, liquido e quantidade;
  - exportacao CSV/Excel/PDF preservando filtros aplicados;
  - painel com filtros avancados e tabela detalhada;
  - tabela `produto_de_para` por empresa, usando `codigo_produto_local` como referencia principal.
- Migration nova:
  - `backend/db/migrations/v006_sales_report_detail_fields.py`.
- Documentacao nova:
  - `docs/relatorios_comerciais_financeiros.md`.

### Validacao local
- `py -3 -m compileall backend sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_sync_upsert.py tests\test_sync_admin_rbac.py -q` -> `12 passed`.
- `py -3 -m pytest -q` -> `41 passed, 1 skipped`.

### Proximo passo seguro
1. Revisar visualmente `/reports` e `/client/reports`.
2. Aplicar migration v006 no ambiente alvo antes do deploy.
3. Subir branch/PR e validar exportacoes com dados reais do cliente.

## Checkpoint referencia XD Software - 2026-04-29

### Arquivo consultado
- `TABELAS DO BANCO XD/REFERENCIA TABELAS BD XD SOFTWARE.xlsx`

### Entrega local adicional
- `agent_local/db/xd_sales_mapper.py` agora usa a referencia XD para fallback automatico:
  - origem preferencial: `salesdocumentsreportview`;
  - origem alternativa: `Documentsbodys + Documentsheaders`;
  - pagamentos: `Invoicepaymentdetails + Xconfigpaymenttypes`;
  - familia: `Itemsgroups`;
  - codigo local do produto: `ItemKeyId -> codigo_produto_local`.
- Criadas rotas de diagnostico no `sync-admin`:
  - `GET /settings/xd-mapping`;
  - `GET /settings/xd-mapping/routes`.
- O diagnostico mostra tabelas/colunas detectadas e tipo de origem usada sem expor senha.

### Validacao local
- `py -3 -m pytest tests\test_xd_sales_mapper.py tests\test_sync_admin_rbac.py tests\test_sync_upsert.py -q` -> `16 passed`.
- `py -3 -m pytest -q` -> `45 passed, 1 skipped`.

## Checkpoint CRUD DE/PARA Produtos - 2026-04-29

### Entrega local adicional
- CRUD administrativo completo de `produto_de_para`:
  - `GET /admin/tenants/{empresa_id}/produto-de-para`;
  - `POST /admin/tenants/{empresa_id}/produto-de-para`;
  - `PUT /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`;
  - `DELETE /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`;
  - `GET /admin/tenants/{empresa_id}/produto-de-para/unmapped`.
- Tela `/settings` recebeu secao `DE/PARA Produtos`:
  - cadastro manual;
  - edicao;
  - remocao;
  - produtos sincronizados sem mapeamento.
- Implementadas camadas separadas:
  - repository;
  - service;
  - schemas;
  - rotas API;
  - client do `sync-admin`.
- Regras aplicadas:
  - isolamento por `empresa_id`;
  - `cnpj` deve bater com `empresa_id`;
  - `codigo_produto_local` permanece como chave principal;
  - auditoria administrativa em criacao, atualizacao e remocao.

### Validacao local
- `py -3 -m compileall agent_local backend sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_produto_de_para.py tests\test_sync_admin_rbac.py tests\test_xd_sales_mapper.py tests\test_sync_upsert.py -q` -> `20 passed`.
- `py -3 -m pytest -q` -> `49 passed, 1 skipped`.

### Autorizacoes operacionais
- Arquivo criado:
  - `docs/autorizacoes_operacionais.md`
- Objetivo:
  - registrar autorizacoes recorrentes para Git, SSH, deploy VPS, migrations e validacoes sem rediscutir o fluxo a cada execucao.

### Deploy VPS executado - 2026-04-29
- Branch em producao:
  - `main`
- Commit funcional em producao:
  - `b198512` - `Expand commercial reporting and XD product mapping`
- PR final mergeado:
  - `#21` - `Expand commercial reporting and XD product mapping`
- Commit funcional do deploy:
  - `902bccd` - `feat: expand commercial reporting module`
- Commit de autorizacoes/documentacao:
  - `8f1f9b4` - `docs: record deployment authorization and VPS status`
- Comando executado na VPS:
  - `bash infra/scripts/deploy-prod.sh`
- Resultado do deploy:
  - build backend/frontend OK;
  - containers recriados;
  - migration aplicada com `current_version=6`;
  - `integrado-backend` healthy;
  - `integrado-frontend` healthy;
  - `integrado-nginx` healthy.
- Validacao publica:
  - `https://movisystecnologia.com.br/healthz` -> `200`;
  - `https://movisystecnologia.com.br/readyz/backend` -> `200`;
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `200`;
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `200`.
- Validacao de schema na VPS:
  - `version=6`;
  - `produto_de_para=produto_de_para`;
  - `vendas_detail_columns=5`.
- Validacao de rotas backend na VPS:
  - `/admin/tenants/12345678000199/reports/overview` -> `200`;
  - `/admin/tenants/12345678000199/produto-de-para?limit=1` -> `200`;
  - `/admin/tenants/12345678000199/produto-de-para/unmapped?limit=1` -> `200`.
- Antes do checkout, a VPS tinha alteracoes locais. Elas foram preservadas em stash e em `infra/deploy-safety/`.
- A branch temporaria foi sincronizada com `origin/main` apos o deploy:
  - merge commit local/remoto: `ef3030a`;
  - `py -3 -m pytest -q` -> `49 passed, 1 skipped`;
  - PR `#21` mergeado em `main` com squash;
  - VPS atualizada para `main` e deploy executado novamente;
  - `scripts/db_migrate.py` retornou `no pending migrations (current_version=6)`.
- Ajuste operacional apos deploy:
  - `infra/nginx/default.conf` e `infra/scripts/*` foram restaurados para o estado rastreado em `main`;
  - `nginx -t` OK;
  - `nginx -s reload` OK;
  - health HTTPS continuou `200`.
- Estado Git da VPS apos limpeza:
  - arquivos rastreados limpos;
  - permanecem somente artefatos locais nao versionados:
    - `infra/backups/postgres_20260429_030001.sql.gz`;
    - `infra/deploy-safety/`;
    - `infra/nginx/certs/accounts/`.

## Checkpoint UX relatorios cliente - 2026-04-29

### Entrega local
- Portal cliente `/client/reports` passa a abrir como dashboard resumido.
- Relatorios detalhados passam a ser acessados por atalhos:
  - `report_view=daily_revenue`;
  - `report_view=payments`;
  - `report_view=products`;
  - `report_view=families`;
  - `report_view=terminals`;
  - `report_view=sales`.
- Filtros avancados foram movidos para bloco recolhivel.
- Relatorios dedicados exibem conteudo isolado por assunto, reduzindo poluicao visual.

### Validacao local
- `py -3 -m compileall sync-admin\app` -> OK.
- `py -3 -m pytest tests\test_sync_admin_rbac.py -q` -> `10 passed`.
- `py -3 -m pytest -q` -> `49 passed, 1 skipped`.

### Deploy VPS
- PR:
  - `#23` - `Split client reports into dashboard and drilldown views`
- Commit em producao:
  - `33eb235` - `Split client reports into dashboard and drilldown views`
- Deploy:
  - `bash infra/scripts/deploy-prod.sh`
  - `MIGRATION OK - no pending migrations (current_version=6)`
- Validacao:
  - `integrado-backend` healthy;
  - `integrado-frontend` healthy;
  - `integrado-nginx` healthy;
  - `https://movisystecnologia.com.br/healthz` -> `200`;
  - `https://movisystecnologia.com.br/readyz/backend` -> `200`;
  - `https://movisystecnologia.com.br/readyz/sync-admin` -> `200`;
  - `https://movisystecnologia.com.br/admin/api/health/ready` -> `200`.
- Ajuste operacional:
  - `infra/nginx/default.conf` restaurado para o estado rastreado;
  - `nginx -t` OK;
  - `nginx -s reload` OK.

## Objetivo desta nota
Este arquivo e o ponto de entrada para retomar o projeto sem redescobrir contexto.

## Estado atual (validado)
- Checkpoint mais recente: hotfix de rotas do painel admin e schema de relatorios em producao.
- Branch local atual: `codex/fix-connected-apis-nginx`.
- Commit local anterior nesta branch: `2a41261` - `fix: route connected apis through nginx`.
- Existem mudancas locais staged ainda sem commit porque a sessao foi interrompida antes do commit final.
- Arquivos staged neste checkpoint:
  - `backend/models/venda.py`
  - `backend/repositories/venda_repository.py`
  - `backend/schemas/sync.py`
  - `backend/sql/postgresql_schema.sql`
  - `infra/nginx/default.conf`
  - `tests/test_production_operations.py`
  - `tests/test_sync_upsert.py`
- VPS ativa em `172.238.213.72` com stack em `/opt/integrado_web_xd`.
- Deploy de producao com `docker-compose.prod.yml`.
- Containers esperados:
  - `integrado_nginx`
  - `integrado_backend`
  - `integrado_frontend`
  - `integrado_db`
- Dominio principal ativo:
  - `https://movisystecnologia.com.br/` redireciona para `/MoviRelatorios/`
  - Cliente em `https://movisystecnologia.com.br/MoviRelatorios`
  - API/Docs em `https://movisystecnologia.com.br/admin`
- SSL ativo (Let's Encrypt) com renovacao automatizada ja preparada.

## Checkpoint operacional mais recente - 2026-04-27

### Problema reportado
- Tela `APIs Conectadas` retornava `404 Not Found` pelo Nginx.
- Tela `Relatorios` tambem retornava `404 Not Found`.
- Apos corrigir o roteamento, a tela `Relatorios` autenticada retornou `500 Internal Server Error`.

### Causas confirmadas
- O `sync-admin` usa links absolutos como `/connected-apis`, `/reports` e `/client/reports`.
- A aplicacao esta publicada sob `/admin`, mas o Nginx so tinha compatibilidade para alguns caminhos absolutos (`/dashboard`, `/settings`, etc.).
- O 500 de relatorios vinha do backend central:
  - endpoint: `GET /admin/tenants/12345678000199/reports/overview`
  - erro: `column vendas.branch_code does not exist`
- O codigo de relatorios esperava `branch_code` e `terminal_code`, mas o schema real do PostgreSQL ainda nao tinha essas colunas.

### Correcao aplicada diretamente na VPS
- `infra/nginx/default.conf` copiado para `/opt/integrado_web_xd/infra/nginx/default.conf`.
- Nginx validado e recarregado:
  - `nginx -t` OK
  - `nginx -s reload` OK
- Migração SQL segura aplicada no PostgreSQL de producao:
  - `ALTER TABLE vendas ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);`
  - `ALTER TABLE vendas ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);`
  - `ALTER TABLE vendas_historico ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);`
  - `ALTER TABLE vendas_historico ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);`
  - `CREATE INDEX IF NOT EXISTS ix_vendas_empresa_branch ON vendas (empresa_id, branch_code);`
  - `CREATE INDEX IF NOT EXISTS ix_vendas_empresa_terminal ON vendas (empresa_id, terminal_code);`

### Validacao em producao executada
- Login admin:
  - usuario: `admin`
  - senha operacional temporaria usada nesta sessao: `MoviSys@2026#Admin`
  - `POST /admin/login` -> `302`
- `GET https://movisystecnologia.com.br/connected-apis` autenticado -> `200`
- `GET https://movisystecnologia.com.br/admin/connected-apis` autenticado -> `200`
- `GET https://movisystecnologia.com.br/reports` autenticado -> `200`
- `GET https://movisystecnologia.com.br/admin/reports` autenticado -> `200`

### Correcao registrada no codigo local
- Nginx:
  - adicionadas rotas compativeis para `/connected-apis`, `/reports` e `/client/reports`.
- Backend:
  - `Venda` e `VendaHistorico` agora incluem `branch_code` e `terminal_code`.
  - `VendaPayload` agora aceita `branch_code` e `terminal_code`.
  - `VendaRepository.bulk_upsert` persiste e atualiza esses campos.
  - `retain_recent_data` arquiva esses campos em `vendas_historico`.
  - `backend/sql/postgresql_schema.sql` inclui colunas, alter idempotente e indices.
- Testes:
  - contrato Nginx cobre `/connected-apis`, `/reports` e `/client/reports`.
  - upsert cobre persistencia e update de `branch_code`/`terminal_code`.

### Validacao local executada
- `py -3 -m pytest tests/test_production_operations.py -q` -> `8 passed`.
- `py -3 -m pytest tests/test_sync_upsert.py tests/test_production_operations.py -q` -> `11 passed`.
- `py -3 -m pytest -q` -> `26 passed, 1 skipped`.

### Estado Git exato ao pausar
- Branch: `codex/fix-connected-apis-nginx`.
- Worktree com arquivos staged e sem commit final.
- Commit que ainda precisa ser criado:
  - sugestao: `fix: restore reports route and sales branch schema`
- Depois do commit:
  - `git push -u origin codex/fix-connected-apis-nginx`
  - abrir/atualizar PR: `https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD/pull/new/codex/fix-connected-apis-nginx`
- Observacao: `main` esta protegida; nao usar push direto para `main`.

## Correcao mais recente aplicada
- Problema reportado: `https://movisystecnologia.com.br/admin/docs` mostrava `Failed to load API definition`.
- Causa: Swagger em `/admin/docs` solicitava `'/openapi.json'` na raiz e o Nginx nao roteava essa URL para o backend.
- Correcao: adicionadas rotas dedicadas no Nginx:
  - `location = /openapi.json`
  - `location = /docs/oauth2-redirect`
- Arquivo alterado:
  - `infra/nginx/default.conf`
- Commit local desta correcao:
  - `34d467f` - `fix(nginx): expose openapi route for swagger under /admin/docs`

## Validacoes de runtime executadas
- `/admin/docs` -> `200 OK`
- `/openapi.json` -> `200 OK`
- Containers backend/frontend/db em estado `healthy`
- Nginx ativo com portas `80/443` publicadas

## Teste real de comunicacao local -> web (2026-04-22)
- Fluxo validado conforme arquitetura:
  - Cliente local (simulado com `agent_local` contract) enviando para `POST /sync`
  - Entrada publica usada: `https://movisystecnologia.com.br/admin/api/sync`
  - Headers: `X-Empresa-Id` + `X-API-Key`
- Resultado de integracao:
  - 1a chamada: `inserted_count=1`, `updated_count=0`
  - 2a chamada (mesmo `uuid`): `inserted_count=0`, `updated_count=1`
  - Banco central confirmou UPSERT com valor final atualizado.
- Validacao de seguranca:
  - Chave invalida retorna `401` com `Credenciais invalidas.`

## Teste real multi-tenant (segundo cliente) - 2026-04-22
- Tenant de teste adicional provisionado: `99887766000155` (Cliente Teste B).
- Insert real executado em `POST https://movisystecnologia.com.br/admin/api/sync` com API key propria.
- Resultado: `200` com `inserted_count=1`.
- Isolamento validado no banco central:
  - registro presente em `empresa_id=99887766000155`
  - `count=0` para o mesmo `uuid` em `empresa_id=12345678000199`

## Painel real de administracao de APIs (2026-04-22)
- Backend admin expandido com gestao real de tenants/API:
  - `GET /admin/tenants` (listagem)
  - `DELETE /admin/tenants/{empresa_id}` (desativacao)
- Painel `settings` atualizado com tabela operacional:
  - lista de clientes (empresa_id, nome, status)
  - acao de rotacionar chave por cliente
  - acao de desativar API por cliente
- Validacao executada em producao:
  - tenant temporario criado, listado como ativo, desativado e listado como inativo.

## Vinculacao por codigo (device code) - implementado no repo (2026-04-22)
- Objetivo: instalar API local no cliente sem expor IP, SSH, usuario ou senha.
- Fluxo novo:
  - Admin gera codigo temporario no painel (`/settings`) por `empresa_id`.
  - Cliente local informa apenas o codigo no agente.
  - Backend valida o codigo (uso unico + expiracao) e devolve API key de agente.
  - Agente salva chave localmente e passa a sincronizar em `POST /sync`.
- Endpoints novos:
  - `POST /admin/tenants/{empresa_id}/pairing-codes` (admin)
  - `POST /agent/pairings/activate` (publico com codigo)
- Seguranca:
  - codigo em hash no banco, expira (TTL), nao reutilizavel.
  - chave gerada vinculada ao `empresa_id` correto, mantendo isolamento multi-tenant.
- Tela local para tecnico (nova):
  - `python -m agent_local.pairing_ui`
  - atalho PowerShell: `scripts/open-agent-pairing-ui.ps1`
  - finalidade: duas abas para operacao de campo:
    - `Vinculacao por Codigo` (onboarding sem editar `.env`)
    - `Configuracao Manual` (troca de URL do servidor/VPS + chave manual)
  - protecao solicitada:
    - alteracao manual de servidor/chave exige senha local
    - senha agora prioriza Windows Credential Manager:
      - target: `MoviSync.ManualConfig.Password`
      - script de cadastro: `scripts/set-agent-manual-password.ps1`
    - fallback opcional por `.env`: `AGENT_MANUAL_CONFIG_PASSWORD`

## Risco importante observado
- Durante ajuste manual houve loop de restart do Nginx por BOM no arquivo de config (`unknown directive "﻿upstream"`).
- Mitigacao aplicada: arquivo salvo sem BOM e Nginx reiniciado com sucesso.
- Regra daqui para frente: evitar edicao de `infra/nginx/default.conf` com BOM.

## Como retomar em 2 minutos
1. Entrar na VPS por chave:
   - script local: `infra/scripts/ssh-prod.ps1`
2. Confirmar stack:
   - `docker ps`
3. Validar rotas principais:
   - `curl -I https://movisystecnologia.com.br/admin/docs`
   - `curl -I https://movisystecnologia.com.br/openapi.json`
   - `curl -I https://movisystecnologia.com.br/MoviRelatorios/`
4. Se houver mudancas pendentes no repo, subir deploy:
   - `infra/scripts/deploy-prod.sh` (na VPS)

## Proximos passos recomendados (curto prazo)
1. Fazer push do commit `34d467f` e merge em `main` para manter convergencia repo <-> VPS.
2. Executar deploy via GitHub Actions em `main` e validar rotas publicas novamente.
3. Opcional tecnico: migrar docs da API para `docs_url='/admin/docs'` + `root_path='/admin'` no FastAPI para eliminar dependencia do alias `/openapi.json`.

## Checkpoint de convergencia backend/VPS - 2026-04-27
- Problema confirmado:
  - a VPS tinha funcionalidades avancadas em arquivos locais/dirty que nao estavam no `main` oficial;
  - ao alinhar a VPS com `origin/main`, houve downgrade funcional do backend;
  - sintomas em producao: `/reports` autenticado retornava `500` por endpoints backend ausentes (`/admin/tenants/{empresa_id}/reports/overview`, `/api/v1/clients`, `/api/v1/clients/summary`).
- Correcao aplicada em branch isolada:
  - branch local: `codex/restore-backend-reporting-contract`;
  - restaurado o contrato backend avancado a partir de `origin/codex/vps-https-deploy-contract`;
  - incluidos endpoints de relatorios por tenant, APIs remotas conectadas, pareamento por codigo, health/readiness avancado, auditoria com `correlation_id`, metricas HTTP e fila/scheduler avancados;
  - corrigido o wiring do `tenant_pairing_router` no FastAPI;
  - ajustada politica de retry do worker para nao enviar falhas permanentes para DLQ na primeira tentativa.
- Validacao local:
  - `py -3 -m pytest tests/test_production_operations.py tests/test_sync_upsert.py tests/test_api_integration.py -q` -> `13 passed`;
  - `py -3 -m pytest tests/test_tenant_scheduler.py -q` -> `3 passed`;
  - `py -3 -m pytest -q` -> `26 passed, 1 skipped`.
- Estado Git esperado:
  - commit pendente na branch `codex/restore-backend-reporting-contract`;
  - depois do commit: push, PR para `main`, merge aprovado e deploy na VPS.
- Regra operacional:
  - nao alinhar VPS com `main` sem validar antes se as funcionalidades existentes em producao estao versionadas;
  - qualquer hotfix manual em VPS deve virar commit/PR antes de novo reset/redeploy.

## Evolucao de relatorios cliente/admin - 2026-04-27
- Decisao de produto:
  - relatorios saem da navegacao principal do admin;
  - admin mantem `/reports` apenas como tela tecnica de teste/validacao;
  - uso operacional principal fica no portal cliente em `/client/reports`.
- Backend:
  - venda canonica agora aceita dimensoes opcionais:
    - `tipo_venda`
    - `forma_pagamento`
    - `familia_produto`
  - adicionada migracao `v005_sales_report_dimensions`;
  - relatorios ganharam filtro por horario (`start_time`, `end_time`) usando `data_atualizacao`;
  - novo endpoint: `/admin/tenants/{empresa_id}/reports/breakdown` com `group_by` em `tipo_venda`, `forma_pagamento` ou `familia_produto`.
- Painel:
  - filtros adicionados:
    - vendas do dia
    - mensal
    - trimestral
    - semestral
    - anual
    - datas X a Y
    - horario X a Y
  - graficos separados:
    - serie diaria
    - top produtos
    - tipo de venda
    - forma de pagamento
    - familia de produto
- Validacao:
  - `py -3 -m pytest -q` -> `27 passed, 1 skipped`.
- Deploy final:
  - branch em producao: `codex/restore-backend-reporting-contract`;
  - commit em producao: `fd8fb8b`;
  - migracao aplicada na VPS: `current_version=5`;
  - containers saudaveis: `integrado-backend`, `integrado-frontend`, `integrado-nginx`, `integrado-db`;
  - smoke autenticado na VPS:
    - `health=200`
    - `ready=200`
    - `login=302`
    - `reports=200`
    - `connected_apis=200`
- Pendente critico:
  - abrir/mergear PR da branch `codex/restore-backend-reporting-contract` em `main`;
  - nao fazer deploy automatico de `main` antes do merge, para nao perder a evolucao dos relatorios.

## Hotfix portal cliente para admin - 2026-04-28

### Problema reportado
- Ao acessar o portal cliente autenticado como admin, a aplicacao retornava:
  - `{"detail":"Acesso restrito ao portal do cliente."}`

### Decisao tecnica
- Admin deve conseguir abrir todos os portais de cliente em modo suporte/validacao.
- Usuario `client` continua restrito ao proprio `empresa_id` e ao proprio escopo de filiais.
- Admin precisa resolver o tenant pelo parametro `empresa_id`, mantendo o isolamento multi-tenant explicito.

### Correcao aplicada
- Novo guard web:
  - `require_client_portal_access`
  - aceita `client` com `empresa_id`;
  - aceita `admin`;
  - rejeita demais perfis.
- Rotas ajustadas para admin preview:
  - `/client/dashboard?empresa_id=<empresa_id>`
  - `/client/reports?empresa_id=<empresa_id>`
  - `/client/reports/export.csv?empresa_id=<empresa_id>`
  - `/client/reports/export.xlsx?empresa_id=<empresa_id>`
  - `/client/reports/export.pdf?empresa_id=<empresa_id>`
- Templates do portal cliente agora exibem aviso de visualizacao administrativa quando o acesso for feito por admin.

### Arquivos principais
- `sync-admin/app/web/deps.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/client_dashboard.html`
- `sync-admin/app/templates/client_reports.html`
- `tests/test_sync_admin_rbac.py`

### Validacao local
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### Deploy VPS
- Branch em producao:
  - `codex/restore-backend-reporting-contract`
- Commit em producao:
  - `c258d71` - `fix: allow admin client portal preview`
- Deploy executado com sucesso via:
  - `bash infra/scripts/deploy-prod.sh`
- Containers validados como saudaveis:
  - `integrado-backend`
  - `integrado-frontend`
  - `integrado-nginx`
  - `integrado-db`

### Links operacionais
- Portal cliente como admin:
  - `https://movisystecnologia.com.br/admin/client/dashboard?empresa_id=12345678000199`
- Relatorios cliente como admin:
  - `https://movisystecnologia.com.br/admin/client/reports?empresa_id=12345678000199`

### Estado Git
- Branch local atual:
  - `codex/restore-backend-reporting-contract`
- Ultimo commit:
  - `c258d71` - `fix: allow admin client portal preview`
- Push ja executado para GitHub.
- `gh` local esta sem autenticacao:
  - `gh auth status` -> nao autenticado.

### Pendente obrigatorio
- Reautenticar GitHub CLI ou usar navegador para abrir/atualizar PR.
- Mergear `codex/restore-backend-reporting-contract` em `main`.
- Depois do merge, voltar a VPS para seguir `main` e validar que nao houve downgrade.

## Hotfix navegacao admin para portal cliente - 2026-04-28

### Decisao operacional
- Admin deve ter acesso a todas as telas do sistema, inclusive telas do portal cliente.
- O acesso admin ao portal cliente continua multi-tenant seguro:
  - sempre com `empresa_id` explicito ou fallback operacional `CONTROL_EMPRESA_ID`;
  - perfil `client` continua preso ao proprio tenant.

### Correcao aplicada
- `admin` recebeu permissoes explicitas:
  - `client.dashboard.view`
  - `client.reports.view`
- Menu lateral do admin agora exibe:
  - `Portal Cliente`
  - `Relatórios Cliente`
- Links usam `settings.control_empresa_id` para abrir um tenant padrao sem URL manual.

### Arquivos alterados
- `sync-admin/app/web/deps.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/base.html`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `28 passed, 1 skipped`

### Controle de conflito PR
- Antes do push foi executado:
  - `git fetch origin`
  - merge de `origin/main`
  - conflito resolvido localmente em `tests/test_sync_admin_rbac.py`
  - suite completa verde
- Commits relevantes:
  - `5844f52` - `fix: expose client portal navigation to admin`
  - `026fa96` - `merge main after admin portal navigation update`
- Push ja executado para `codex/restore-backend-reporting-contract`.

## Modernizacao BI do painel de relatorios - 2026-04-28

### Decisao tecnica
- Evoluir o painel atual sem reescrever o stack para React neste ciclo.
- Manter arquitetura existente:
  - backend central FastAPI/SQLAlchemy;
  - sync-admin em FastAPI + Jinja;
  - graficos via Chart.js;
  - exportacoes existentes preservadas.
- Implementar uma superficie visual de BI comercial com baixo risco e compatibilidade com producao.

### Entregue
- Dashboard de relatorios com visual SaaS/BI:
  - header executivo;
  - filtros globais;
  - cards de KPI;
  - graficos de linha, barra e donut;
  - comparativo com periodo anterior;
  - status da API local;
  - tabela detalhada com busca e ordenacao local;
  - layout responsivo desktop/tablet/celular;
  - tema claro/escuro por toggle.
- KPIs adicionados:
  - total faturado;
  - total de registros;
  - ticket medio;
  - crescimento percentual;
  - periodo anterior;
  - ultima sincronizacao;
  - status da API local.
- Endpoints JSON adicionados no sync-admin:
  - caminho publico usado pela UI/Nginx:
    - `GET /reports/api/dashboard`
    - `GET /reports/api/kpis`
    - `GET /reports/api/charts`
    - `GET /reports/api/table`
    - `GET /reports/api/sync-status`
    - `GET /reports/api/export/pdf`
    - `GET /reports/api/export/excel`
    - `GET /reports/api/export/csv`
  - aliases locais preservados:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/kpis`
  - `GET /api/reports/charts`
  - `GET /api/reports/table`
  - `GET /api/reports/sync-status`
  - `GET /api/reports/export/pdf`
  - `GET /api/reports/export/excel`
  - `GET /api/reports/export/csv`
- Atualizacao automatica:
  - dashboard consulta endpoint JSON em intervalo configurado;
  - atualiza KPIs sem reload completo.
- Drill-down inicial:
  - clique em ponto/barra do grafico filtra a tabela detalhada pelo label selecionado.
- Regra de 14 meses:
  - `_resolve_report_period` agora limita a janela de consulta a `MAX_REPORT_WINDOW_DAYS=427`.
  - se usuario enviar intervalo maior, o inicio e ajustado para respeitar a janela maxima.

### Arquivos alterados
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/static/js/reports.js`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `2 passed`
- `py -3 -m pytest -q`
  - Resultado: `29 passed, 1 skipped`

### Pendente recomendado
- Validar visual no navegador/VPS apos merge.
- Em ciclo futuro, se necessario, migrar o frontend para React/Recharts com contrato de API ja preparado.

## Hotfix PDF de relatorios - 2026-04-28

### Problema reportado
- PDF de relatorios era gerado como texto corrido e comprimido.
- Conteudo ficava ilegivel:
  - filtros, KPIs, serie diaria, top produtos e vendas recentes saiam quase em bloco unico.

### Correcao aplicada
- `report_to_pdf_bytes` foi refeito para gerar PDF estruturado:
  - titulo;
  - data de geracao;
  - secao de filtros e resumo;
  - secao de indicadores;
  - tabela de serie diaria;
  - tabela de top produtos;
  - tabela de vendas recentes;
  - paginacao automatica quando o conteudo passa do limite da pagina.
- Implementado renderizador PDF interno `_PdfDocument`, sem dependencia externa.

### Arquivos alterados
- `sync-admin/app/services/export_service.py`
- `tests/test_sync_admin_rbac.py`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `4 passed`
- `py -3 -m pytest -q`
  - Resultado: `30 passed, 1 skipped`

## Hotfix CSV/Excel de relatorios - 2026-04-28

### Problema reportado
- CSV nao estava funcionando.
- Excel estava confuso para o cliente entender.

### Causa
- CSV usava `csv.DictWriter` com campos fixos tecnicos e quebrava quando `recent_items` trazia campos extras.
- Excel exportava abas/cabecalhos tecnicos em ingles:
  - `Overview`
  - `DailySales`
  - `TopProducts`
  - `RecentSales`

### Correcao aplicada
- CSV:
  - passou a ignorar campos extras;
  - usa separador `;`;
  - cabecalhos em portugues:
    - `Data`, `Produto`, `Valor`, `Pagamento`, `Tipo`, `Familia`, `Filial`, `Terminal`, `Codigo`.
- Excel:
  - abas simplificadas:
    - `Resumo`
    - `Vendas`
    - `Produtos`
    - `Dias`
  - cabecalhos em portugues;
  - removeu metricas tecnicas cruas do cliente.

### Arquivos alterados
- `sync-admin/app/services/export_service.py`
- `tests/test_sync_admin_rbac.py`
- `REGISTRO_DE_MUDANCAS.md`

### Validacao
- `py -3 -m compileall sync-admin/app`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py -q`
  - Resultado: `5 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

## Hotfix 404 Portal Cliente - 2026-04-28

### Problema reportado
- Portal do cliente retornava:
  - `404 Not Found`
  - `nginx/1.27.5`

### Causa
- O Nginx tinha rota para `/client/reports`, mas nao tinha rota para `/client/dashboard`.
- O menu do admin e o login do cliente usam link absoluto `/client/dashboard`.

### Correcao aplicada
- Adicionado no Nginx:
  - `location /client/dashboard { proxy_pass http://frontend_upstream; }`
- Teste de contrato atualizado:
  - `tests/test_production_operations.py`

### Validacao
- `py -3 -m pytest tests/test_production_operations.py -q`
  - Resultado: `8 passed`
- `py -3 -m pytest -q`
  - Resultado: `31 passed, 1 skipped`

## Padronizacao visual AdminLTE - 2026-04-28

### Decisao tecnica
- AdminLTE passa a ser a base visual oficial do `sync-admin`.
- Todas as telas autenticadas usam:
  - `main-sidebar`;
  - `main-header navbar`;
  - `content-wrapper`;
  - `content-header`;
  - breadcrumbs;
  - `main-footer`;
  - cards, small-boxes, badges, alerts e tabelas no padrao AdminLTE.

### Entregue
- Login migrado para layout AdminLTE (`login-page`, `login-box`, `card-outline`).
- Menu lateral padronizado com:
  - Dashboard;
  - Relatorios;
  - Empresas;
  - Usuarios;
  - APIs conectadas;
  - Sincronizacoes;
  - Logs;
  - Configuracoes;
  - Backup;
  - Sair.
- Relatorios migrados para BI com AdminLTE:
  - KPIs em `small-box`;
  - graficos em `card card-outline`;
  - filtros compactos em card lateral;
  - ranking executivo;
  - tabela responsiva com busca, ordenacao e paginacao local;
  - exportacao CSV, Excel e PDF preservada.
- Criado partial reutilizavel:
  - `sync-admin/app/templates/partials/adminlte_components.html`.
- Filtro de categoria agora tambem e aplicado no backend por produto/familia, sempre com `empresa_id`.

### Arquivos principais
- `sync-admin/app/templates/base.html`
- `sync-admin/app/templates/login.html`
- `sync-admin/app/templates/partials/report_dashboard_content.html`
- `sync-admin/app/templates/partials/adminlte_components.html`
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/static/js/reports.js`
- `backend/repositories/venda_repository.py`
- `backend/services/tenant_report_service.py`
- `backend/api/routes/tenant_admin.py`
- `sync-admin/app/services/control_service.py`
- `sync-admin/app/web/routes/pages.py`

### Validacao
- `py -3 -m compileall sync-admin/app backend`
  - OK
- `py -3 -m pytest tests/test_sync_admin_rbac.py tests/test_sync_upsert.py tests/test_sync_admin_sync_cockpit.py -q`
  - Resultado: `14 passed`
- `py -3 -m pytest -q`
  - Resultado: `33 passed, 1 skipped`

## Checkpoint visual AdminLTE em producao - 2026-04-28

### Contexto
- O painel de relatorios foi padronizado com AdminLTE, mas a validacao visual real mostrou problemas de proporcao:
  - KPIs estreitos/verticais;
  - filtros laterais com overflow horizontal;
  - cabecalho `Filtros globais` e resumo de chips estourando a largura do card.

### Correcoes aplicadas
- `fix: normalize AdminLTE report layout proportions`
  - Commit: `8a7bdb9`
  - Corrigiu proporcao dos KPIs e conflitos entre grid proprio e `.row` do AdminLTE.
- `fix: prevent report filter sidebar overflow`
  - Commit: `3eaa85d`
  - Corrigiu overflow horizontal do painel lateral de filtros.
  - Ajustou inputs/selects, grid compacto e chips verticais.
- `fix: contain report filter header overflow`
  - Commit: `7cc6729`
  - Corrigiu estouro do cabecalho `Filtros globais`.
  - Isolou classe `bi-filter-head`.
  - Ajustou `card-title`, descricao e chips de resumo com reticencias.

### Arquivos principais
- `sync-admin/app/static/css/app.css`
- `sync-admin/app/templates/partials/report_dashboard_content.html`

### Validacao
- `py -3 -m compileall sync-admin\app`
  - OK
- Deploy VPS aplicado na branch:
  - `codex/restore-backend-reporting-contract`
- VPS atualizada para:
  - `7cc6729`
- Containers validados:
  - `integrado-frontend` healthy
  - `integrado-nginx` healthy
- Smoke externo:
  - `https://movisystecnologia.com.br/healthz`
  - Resultado: `ok`

### Estado atual para retomada
- Workspace local estava limpo antes deste checkpoint documental.
- Producao esta alinhada com a branch `codex/restore-backend-reporting-contract`.
- O bug visual reportado do bloco `Filtros globais` foi tratado no CSS e publicado.
- Proxima acao recomendada:
  - validar visual no navegador em `https://movisystecnologia.com.br/client/dashboard`;
  - se estiver aprovado, abrir/atualizar PR para merge em `main`;
  - apos merge, manter VPS seguindo `main`.

## Evolucao API Local - painel de banco por formulario - 2026-04-28

### Decisao
- Manter a arquitetura correta para cliente real:
  - credenciais do banco ficam no agente local;
  - API web recebe apenas dados sincronizados;
  - admin web acompanha status e pode operar a API conectada;
  - cliente nao precisa editar JSON para configurar o banco.

### Entregue
- Criado servico local de configuracao de banco:
  - `agent_local/config/database_config.py`
- Painel local `agent_local/pairing_ui.py` evoluido para `MoviSync - Painel Local`.
- Nova aba `Banco Local` com:
  - tipo do banco;
  - host/IP;
  - porta;
  - nome do banco;
  - usuario;
  - senha;
  - SSL;
  - intervalo de sincronizacao;
  - tamanho do lote;
  - arquivo `.env`.
- Botoes adicionados:
  - `Testar banco`;
  - `Salvar banco`.
- O painel salva automaticamente:
  - `AGENT_MARIADB_URL`;
  - `SYNC_INTERVAL_MINUTES`;
  - `BATCH_SIZE`.
- Instalador local atualizado para criar tambem:
  - `Abrir_Painel_Local.cmd`
- Atalho antigo preservado:
  - `Abrir_Vinculacao.cmd`

### Arquivos principais
- `agent_local/config/database_config.py`
- `agent_local/pairing_ui.py`
- `infra/client-agent/install-agent-client.ps1`
- `infra/client-agent/README.md`
- `infra/client-agent/RELEASES.md`
- `tests/test_agent_local_database_config.py`

### Validacao
- `py -3 -m compileall agent_local`
  - OK
- `py -3 -m pytest tests\test_agent_local_database_config.py tests\test_agent_pairing_service.py -q`
  - Resultado: `3 passed`
- `py -3 -m pytest -q`
  - Resultado: `35 passed, 1 skipped`
- Smoke de pacote instalador:
  - `powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1 -VersionTag local-panel-smoke -OutputRoot .\output\client-agent-releases`
  - Resultado: release gerada em `output/client-agent-releases/local-panel-smoke`

### Proximo passo recomendado
- Commitar e publicar esta evolucao.
- Depois criar release versionada oficial do instalador se for distribuir para cliente.

## Teste ponta a ponta MariaDB local -> API web -> relatorios - 2026-04-28

### Objetivo
- Validar o fluxo real solicitado:
  - banco MariaDB local;
  - agente/API local;
  - envio para API web em producao;
  - visualizacao posterior no portal do cliente.

### Ambiente usado
- Branch local:
  - `codex/local-agent-db-panel`
- API web:
  - `https://movisystecnologia.com.br/admin/api`
- Tenant:
  - `12345678000199`
- Banco local:
  - MariaDB em `127.0.0.1:3308/xd`
- Query local:
  - `AGENT_SOURCE_QUERY` do `agent_local/.env.example`
- Checkpoint runtime local:
  - `agent_local/data/checkpoints.json`
- Chave runtime local:
  - `agent_local/data/agent_api_key.txt`
  - adicionada ao `.gitignore` para nunca versionar.

### Passos executados
- Criado codigo temporario de pareamento na VPS para o tenant `12345678000199`.
- Ativado o agente local com o codigo gerado.
- Gerada chave local do agente em `agent_local/data/agent_api_key.txt`.
- Configuracao MariaDB salva no `.env` local via novo servico do painel:
  - `AGENT_MARIADB_URL`;
  - `AGENT_SOURCE_QUERY`;
  - `SYNC_INTERVAL_MINUTES`;
  - `BATCH_SIZE`;
  - `CHECKPOINT_FILE`.
- Teste de conexao MariaDB:
  - `mariadb_ping=True`
- Amostra antes do envio:
  - havia registros pendentes apos checkpoint `2026-01-14T11:17:44+00:00`.
- Rodado ciclo unico do `SyncRunner`.

### Resultado da sincronizacao
- API web retornou:
  - `status`: `ok`
  - `empresa_id`: `12345678000199`
  - `inserted_count`: `484`
  - `updated_count`: `0`
  - `processed_count`: `484`

### Resultado do relatorio web
- Endpoint administrativo de relatorios em producao confirmou:
  - periodo: `2026-01-14` ate `2026-04-28`
  - `total_records`: `485`
  - `total_sales_value`: `20132.21`
  - `distinct_products`: `103`
  - `first_sale_date`: `2026-01-14`
  - `last_sale_date`: `2026-04-22`

### Links para verificar visualmente
- Portal cliente:
  - `https://movisystecnologia.com.br/client/dashboard?empresa_id=12345678000199`
- Relatorios cliente com periodo usado no teste:
  - `https://movisystecnologia.com.br/client/reports?empresa_id=12345678000199&start_date=2026-01-14&end_date=2026-04-28`

### Cuidados tomados
- A chave local do agente nao foi exibida no log.
- A chave local do agente foi ignorada no Git:
  - `.gitignore`
  - `agent_local/data/agent_api_key.txt`
- O checkpoint runtime alterado pelo teste nao foi commitado.

### Commits relacionados
- `e6a4b7d` - `feat: add local agent database setup panel`
- `f3ba66e` - `chore: ignore local agent runtime key`

### Estado para continuar depois
- O fluxo local -> web esta provado com dados reais.
- A branch `codex/local-agent-db-panel` esta publicada.
- PR ainda precisa ser aberta/mergeada na `main`.
- Proximo passo seguro:
  - abrir PR de `codex/local-agent-db-panel` para `main`;
  - apos merge, atualizar VPS para `main`;
  - gerar release versionada oficial do instalador do cliente.

## Checkpoint: primeira carga canonica enriquecida - 2026-04-28

### Objetivo
- Ao configurar a API local, a primeira carga deve transformar o MariaDB local em modelo canonico para relatorios.
- O agente local nao deve enviar estrutura bruta do banco.
- A API web deve receber dimensoes necessarias para BI:
  - `forma_pagamento`;
  - `familia_produto`;
  - `tipo_venda`;
  - `terminal_code`;
  - `branch_code`;
  - metadados de origem (`cnpj`, `company_name`, `payment_methods`).

### Entrega
- Criado auto-mapeamento `AGENT_SOURCE_QUERY=auto`.
- Quando detectar `salesdocumentsreportview`, o agente monta query canonica automaticamente.
- Familia de produto vem de `itemsgroups`.
- Forma de pagamento vem de `invoicepaymentdetails` + `xconfigpaymenttypes`.
- O payload `/sync` passou a preservar campos de relatorio no envio.
- O backend passou a aceitar `source_metadata`.
- O backend rejeita `source_metadata.cnpj` diferente do tenant autenticado.
- O backend atualiza `Tenant.nome` quando a origem local informar `company_name`.

### Validacao
- Teste unitario/local:
  - `py -3 -m pytest -q`
  - resultado: `40 passed, 1 skipped`
- Teste real contra MariaDB local:
  - `source_query=auto`;
  - retornou registro com `branch_code`, `terminal_code`, `tipo_venda`, `forma_pagamento` e `familia_produto`;
  - metadados retornaram `cnpj` e `payment_methods`;
  - `payment_methods_count=7`.

### Proximo passo seguro
- Commitar a entrega.
- Abrir/atualizar PR da branch `codex/local-agent-db-panel`.
- Depois do merge, atualizar VPS.

## Checkpoint: data de venda por criacao sem duplicar UUID - 2026-05-01

### Problema
- Os relatorios devem respeitar a data de criacao da venda no banco local.
- A primeira correcao alterava tambem a base do UUID para `CreationDate`.
- Isso poderia gerar duplicidade ao reprocessar vendas antigas ja sincronizadas.

### Correcao aplicada
- Campo de relatorio `data` usa `CreationDate` com fallback para `CloseDate`.
- Campo `data_atualizacao` continua usando `CloseDate` com fallback para `CreationDate`.
- UUID continua baseado em `CloseDate/CreationDate`, preservando compatibilidade com vendas ja enviadas.
- Checkpoint da sincronizacao continua baseado em `data_atualizacao`.

### Aplicacao local
- Arquivo atualizado no agente instalado:
  - `C:\MoviSyncAgent\agent_local\db\xd_sales_mapper.py`
- Backup antes do reprocessamento:
  - `C:\MoviSyncAgent\backup_reprocess_creation_date_20260501_173840`
- Checkpoint resetado para reprocessar vendas:
  - `12345678000199:vendas=1970-01-01T00:00:00+00:00`
- Banco local validado:
  - origem: `salesdocumentsreportview`;
  - total local: `51475`;
  - ultimo `CloseDate/CreationDate`: `2026-03-28 15:36:02`;
  - ultimo `CreationDate/CloseDate`: `2026-03-28 15:00:13`.
- Reprocessamento em segundo plano:
  - PID inicial validado: `1960`;
  - log: `C:\MoviSyncAgent\logs\reprocess_creation_date_20260501.log`.
- Resultado final:
  - reprocessamento concluiu em `2026-05-01T18:41:58-03:00`;
  - ultimo lote util enviou `64` registros e processou `63`;
  - ciclo seguinte retornou `no_records_to_sync`;
  - checkpoint final: `12345678000199:vendas=2026-03-28T15:36:02+00:00`;
  - autostart local religou API local, tray e sync normal sem tela preta;
  - status local confirmado em `http://127.0.0.1:8765/status` com `sync_running=true`.

### Validacao
- Testes focados:
  - `py -3 -m pytest tests\test_agent_local_sales_mapping.py tests\test_agent_checkpoint_reset.py -q`
  - resultado: `8 passed`
- Compile local:
  - `py -3 -m compileall agent_local -q`

## Checkpoint: valores dos relatorios em moeda BRL - 2026-05-01

### Entrega
- Valores monetarios da tela de relatorios agora usam formato brasileiro:
  - exemplo: `R$ 1.000,00`.
- Valores monetarios ganharam classe visual dedicada:
  - `bi-money`.
- Filtros ficaram mais claros:
  - `Nome do produto`;
  - `Codigo local do produto`.
- Ordenacao numerica da tabela passou a entender valores com `R$`, ponto e virgula.

### Publicacao
- PR: `#44`.
- Commit na main: `e0a9ea1`.
- Deploy producao: sucesso.
- Health producao:
  - `/healthz`: `ok`;
  - `/admin/api/health/ready`: `ready`.

### Validacao
- `py -3 -m pytest tests\test_sync_admin_report_ui.py -q`
  - resultado: `5 passed`
- `py -3 -m pytest tests\test_sync_admin_rbac.py::test_report_dashboard_uses_modern_bi_layout -q`
  - resultado: `1 passed`
- `py -3 -m compileall sync-admin\app -q`
  - resultado: OK

## Checkpoint: usuario cliente padrao e portal separado - 2026-04-28

### Entrega
- Seed automatico do usuario cliente:
  - usuario: `adm`;
  - perfil: `client`;
  - escopo: `company`;
  - empresa padrao: `CONTROL_EMPRESA_ID`;
  - senha configurada por `INITIAL_CLIENT_PASSWORD` e armazenada somente como hash no banco.
- Criado login separado do portal do cliente:
  - `/client/login`;
  - publico via Nginx em `/MoviRelatorios/login`.
- Cliente autenticado vai para:
  - `/client/reports`.
- Cliente nao acessa dashboard/admin:
  - `/dashboard` retorna `403` para perfil `client`.
- Admin continua podendo visualizar o portal cliente para suporte/teste.
- Nginx passou a mapear:
  - `/MoviRelatorios/*` -> `/client/*`;
  - `/admin/*` permanece separado.

### Validacao
- Testes focados:
  - `py -3 -m pytest tests\test_sync_admin_rbac.py tests\test_production_operations.py -q`
  - `15 passed`
- Suite completa:
  - `py -3 -m pytest -q`
  - `40 passed, 1 skipped`

## Checkpoint: diagnostico de travamento da suite local - 2026-05-03

### Problema
- A retomada travou durante reexecucao de testes.
- Processo `pytest` ficou ativo apos interrupcao manual:
  - `py.exe -3 -m pytest tests\test_sync_admin_rbac.py::test_sync_admin_role_based_access -q`
  - `python.exe -m pytest tests\test_sync_admin_rbac.py::test_sync_admin_role_based_access -q`
- O processo preso manteve arquivo SQLite de teste em uso:
  - `output/test_sync_admin_rbac.db`

### Causa raiz
- `test_sync_admin_rbac.py` acessava `/settings` e `/dashboard` sem mockar chamadas externas do `ControlService`.
- `/settings` aguardava timeouts em:
  - fontes de sync;
  - destinos;
  - auditoria remota;
  - server settings;
  - produto DE/PARA.
- `test_sync_admin_sync_cockpit.py` nao mockava `fetch_report_filter_options`; o dashboard tentava API real, caia no fallback zerado e falhava em `commercial_snapshot.total_records`.
- O teste de cockpit dependia implicitamente do mes atual; em maio/2026 a comparacao esperada de abril deixou de ser deterministica.
- O `RemoteAgentService.background_loop` podia atrasar shutdown do `TestClient` quando havia ciclo remoto em andamento.

### Correcao aplicada
- Encerrados apenas processos `pytest` presos.
- `sync-admin/app/main.py` agora cancela `remote_task` no shutdown apos setar o stop event.
- `tests/test_sync_admin_sync_cockpit.py` agora mocka:
  - `fetch_report_filter_options`;
  - `_current_month_range` fixo em `2026-04-01` ate `2026-04-26`.
- `tests/test_sync_admin_rbac.py` agora isola chamadas externas no teste de RBAC:
  - `REMOTE_COMMAND_PULL_ENABLED=false`;
  - mocks de `ControlService` para summary, fontes, jobs, destinos, auditoria, server settings e produto DE/PARA.
- `agent_local/orders/printer.py` sanitiza `command_number` antes de usar em nome de arquivo de job.
- `agent_local/orders/schemas.py` usa `Field(default_factory=list)` em `payments`.

### Validacao
- `py -3 -m pytest tests\test_agent_local_orders.py -q`
  - `7 passed`
- `py -3 -m pytest tests\test_sync_admin_sync_cockpit.py::test_sync_admin_dashboard_exposes_source_cycle_cockpit -q`
  - `1 passed`
- `py -3 -m pytest tests\test_sync_admin_rbac.py::test_sync_admin_role_based_access -q`
  - `1 passed`
- `py -3 -m pytest -q`
  - `76 passed, 1 skipped`

### Proximo passo seguro
- Revisar diff final da frente de comandas locais.
- Se aprovado, commitar entrega local.
- Depois gerar release/instalador versionado do agente com tela de comandas.

## Checkpoint de retomada exata: comandas locais + suite estabilizada - 2026-05-03

### Estado do workspace
- Branch atual:
  - `main`
  - tracking: `origin/main`
- Existem alteracoes locais ainda nao commitadas.
- Nao ha teste `pytest` preso ativo apos a correcao.
- Suite completa validada antes deste checkpoint:
  - `py -3 -m pytest -q`
  - resultado: `76 passed, 1 skipped`

### Arquivos modificados rastreados
- `RETOMADA_EXATA.md`
- `agent_local/.env.example`
- `agent_local/db/mariadb_client.py`
- `agent_local/local_api.py`
- `cerebro_vivo/estado_atual.md`
- `sync-admin/app/main.py`
- `tests/test_sync_admin_rbac.py`
- `tests/test_sync_admin_sync_cockpit.py`

### Arquivos novos ainda nao rastreados
- `agent_local/orders/__init__.py`
- `agent_local/orders/printer.py`
- `agent_local/orders/repository.py`
- `agent_local/orders/schemas.py`
- `agent_local/orders/service.py`
- `scripts/open-local-orders.cmd`
- `scripts/open-local-orders.ps1`
- `tests/test_agent_local_orders.py`
- pasta `licensa lic/`

### Entrega funcional em andamento
- Frente principal:
  - comandas locais no agente.
- Separacao arquitetural obrigatoria:
  - esta API de comandas locais e uma API operacional separada.
  - nao e a mesma API do sync de relatorios.
  - nao deve reaproveitar contrato `/sync` nem tabelas centrais de relatorio para comandas.
  - sync de relatorios continua com responsabilidade exclusiva de envio de vendas/dados canonicos para BI.
  - comandas locais devem ficar isoladas em modulo proprio, banco local proprio e endpoints `/orders`.
  - se no futuro houver integracao entre comandas e relatorios, deve ser por contrato explicito de eventos/exportacao, nao por mistura direta das responsabilidades.
- API local adicionada:
  - `POST /orders`
  - `GET /orders`
  - `POST /orders/{order_uuid}/items`
  - `PATCH /orders/{order_uuid}/items/{item_id}`
  - `DELETE /orders/{order_uuid}/items/{item_id}`
  - `POST /orders/{order_uuid}/close`
  - `POST /orders/{order_uuid}/cancel`
  - `GET /orders/operators`
  - `GET /orders/product-families`
  - `GET /orders/products`
  - `GET /orders/{order_uuid}/prebill`
  - `GET /orders/{order_uuid}/thermal-receipt`
  - `POST /orders/{order_uuid}/print`
  - `GET /orders/ui`
- Persistencia local:
  - SQLite em `LOCAL_ORDER_DB_PATH`
  - tabelas de comandas, itens, pagamentos, operadores, produtos e outbox.
- Catalogo:
  - descoberta automatica no MariaDB XD quando `LOCAL_ORDER_AUTO_REFRESH_CATALOG=true`.
  - produtos a partir de `items` ou fallback `salesdocumentsreportview`.
  - operadores a partir de `xconfigoperators`, `operators`, `employees`, `users` ou fallback em `documentsheaders`.
- Impressao:
  - recibo termico texto.
  - job local em `LOCAL_ORDER_PRINT_JOBS_DIR`.
  - envio ao spool Windows somente quando `LOCAL_ORDER_PRINTER_NAME` estiver configurado.

### Correcoes de estabilidade ja aplicadas
- `sync-admin/app/main.py`
  - cancela `remote_task` no shutdown do lifespan.
- `tests/test_sync_admin_rbac.py`
  - isola chamadas externas de `/settings` e `/dashboard`.
  - define `REMOTE_COMMAND_PULL_ENABLED=false`.
- `tests/test_sync_admin_sync_cockpit.py`
  - mocka `fetch_report_filter_options`.
  - fixa `_current_month_range` em abril/2026 para teste deterministico.
- `agent_local/orders/printer.py`
  - sanitiza `command_number` usado em filename.
- `agent_local/orders/schemas.py`
  - evita lista mutavel default em `payments`.

### Comandos ja validados
- `py -3 -m pytest tests\test_agent_local_orders.py -q`
  - `7 passed`
- `py -3 -m pytest tests\test_sync_admin_sync_cockpit.py::test_sync_admin_dashboard_exposes_source_cycle_cockpit -q`
  - `1 passed`
- `py -3 -m pytest tests\test_sync_admin_rbac.py::test_sync_admin_role_based_access -q`
  - `1 passed`
- `py -3 -m compileall agent_local -q`
  - OK
- `py -3 -m pytest -q`
  - `76 passed, 1 skipped`

### Riscos pendentes antes de commit
- Revisar se a UI embutida em `agent_local/local_api.py` deve continuar inline ou ser separada futuramente.
- Garantir que a API de comandas locais nao seja documentada nem tratada como API de sync de relatorios.
- Conferir se `licensa lic/` faz parte desta entrega antes de incluir no commit.
- Validar manualmente `/orders/ui` no agente instalado se a proxima etapa for gerar release.
- Nao commitar arquivos runtime:
  - bancos SQLite em `output/`;
  - tokens locais;
  - jobs de impressao gerados.

### Proximo passo operacional
1. Rodar `git diff --stat`.
2. Revisar arquivos novos em `agent_local/orders/`.
3. Decidir se `licensa lic/` entra no commit ou fica fora.
4. Se o diff estiver coerente:
   - commitar a entrega de comandas locais;
   - gerar release/instalador versionado do agente;
   - validar `http://127.0.0.1:8765/orders/ui` no ambiente instalado.

## Checkpoint: release oficial do agente com comandas locais - 2026-05-03

### Commits locais
- `0b1fd1d` - `feat: adicionar comandas locais no agente`
- Branch `main` esta `ahead 1` antes do commit do instalador/release.

### Separacao arquitetural reforcada
- API de comandas locais e operacional.
- Nao e a API de sync de relatorios.
- Contrato `/orders` permanece separado de `/sync`.
- Banco local de comandas permanece separado do BI/relatorios.

### Instalador ajustado
- Arquivo:
  - `infra/client-agent/install-agent-client.ps1`
- Agora cria no cliente instalado:
  - `Abrir_Comandas_Locais.cmd`
  - `Abrir_Comandas_Locais.vbs`
  - atalho Desktop `MoviSync Comandas Locais.lnk`
- O atalho valida `http://127.0.0.1:8765/health` antes de abrir:
  - `http://127.0.0.1:8765/orders/ui`

### Release gerada
- Pasta:
  - `infra/client-agent/releases/v2026-05-03_comandas`
- ZIP:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas.zip`
- Tamanho:
  - `150527` bytes
- Conteudo validado:
  - `agent_local/orders/*.py`
  - `install-agent-client.ps1`
  - `requirements.txt`
  - sem `__pycache__`
  - sem `.pyc`

### Validacao executada
- `py -3 -m pytest -q`
  - `76 passed, 1 skipped`
- `py -3 -m pytest tests\test_agent_local_orders.py tests\test_sync_admin_rbac.py::test_sync_admin_role_based_access tests\test_sync_admin_sync_cockpit.py::test_sync_admin_dashboard_exposes_source_cycle_cockpit -q`
  - `9 passed`
- `py -3 -m compileall agent_local sync-admin\app -q`
  - OK
- `py -3 -m compileall infra\client-agent\releases\v2026-05-03_comandas\agent_local infra\client-agent\releases\v2026-05-03_comandas\backend -q`
  - OK
- Parser PowerShell:
  - `infra/client-agent/install-agent-client.ps1`
  - `parse-ok`

### Proximo passo seguro
- Commitar alteracoes do instalador e `RELEASES.md`.
- Depois, se for distribuir:
  - usar `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas.zip`.
- Para validacao real instalada:
  - instalar/atualizar em `C:\MoviSyncAgent`;
  - abrir `MoviSync Comandas Locais.lnk`;
  - confirmar `/orders/ui`;
  - criar comanda teste;
  - validar pre-conta e job de impressao.

## Checkpoint: versao explicita para nao misturar releases - 2026-05-03

### Problema
- O pacote anterior podia confundir porque atalhos e instalacao mantinham nomes iguais aos pacotes antigos.
- O usuario viu a tela `MoviSync - Painel Local`, que pertence ao sync/configuracao, nao a tela de comandas.

### Correcao aplicada
- Nova release oficial para teste:
  - `v2026-05-03_comandas_r2`
- ZIP correto:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas_r2.zip`
- Tamanho:
  - `151236` bytes
- `build-release.ps1` agora gera:
  - `package-version.txt`
- `install-agent-client.ps1` agora:
  - le `package-version.txt`;
  - grava `C:\MoviSyncAgent\VERSAO_INSTALADA.txt`;
  - copia `release-manifest.txt` para `C:\MoviSyncAgent`;
  - remove atalhos antigos `MoviSync *.lnk` da area de trabalho antes de criar novos;
  - cria atalhos com versao no nome.
- Atalho principal esperado:
  - `MoviSync Comandas Locais - v2026-05-03_comandas_r2.lnk`

### Validacao
- Parser PowerShell:
  - `parse-ok`
- Teste focado:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q`
  - `7 passed`
- ZIP validado:
  - `pycache_count=0`
  - `orders_entries=5`
  - `package_version_file=1`

### Proximo teste do usuario
1. Usar somente:
   - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas_r2.zip`
2. Extrair em pasta nova.
3. Rodar `COMECE_AQUI.bat` como administrador.
4. Conferir atalho:
   - `MoviSync Comandas Locais - v2026-05-03_comandas_r2.lnk`
5. Conferir arquivo instalado:
   - `C:\MoviSyncAgent\VERSAO_INSTALADA.txt`
