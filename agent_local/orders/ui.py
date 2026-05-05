from __future__ import annotations


def render_orders_ui() -> str:
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Movi_commanda</title>
  <style>
    :root {
      --bg: #f5f7fa;
      --surface: #ffffff;
      --text: #17212f;
      --muted: #5f6b7a;
      --line: #d7dee8;
      --primary: #1769aa;
      --primary-dark: #124f80;
      --ok: #147d4f;
      --danger: #b42318;
      --warn: #b54708;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, sans-serif; color: var(--text); background: var(--bg); }
    button, input, select, textarea { font: inherit; }
    button { border: 0; cursor: pointer; min-height: 48px; border-radius: 6px; font-weight: 700; }
    input, select, textarea { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 12px; background: #fff; }
    label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .app { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    .topbar { position: sticky; top: 0; z-index: 10; display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; padding: 12px 14px; color: #fff; background: var(--primary-dark); }
    .title { font-size: 20px; font-weight: 800; line-height: 1.1; }
    .subtitle { font-size: 13px; opacity: .9; margin-top: 3px; }
    .user-badge { color: #fff; border: 1px solid #ffffff55; padding: 9px 10px; border-radius: 6px; font-size: 13px; max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .screen { display: none; padding: 14px; }
    .screen.active { display: block; }
    .stack { display: grid; gap: 12px; }
    .grid { display: grid; gap: 12px; }
    .two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .surface { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .actions { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .menu { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .menu button { min-height: 104px; background: var(--surface); color: var(--text); border: 1px solid var(--line); font-size: 18px; }
    .menu-screen { min-height: calc(100vh - 68px); margin: -14px; padding: 16px; color: #fff; background: linear-gradient(160deg, #243b86 0%, #29106f 54%, #1c0b4f 100%); }
    .operator-panel { display: grid; grid-template-columns: 108px 1fr; gap: 12px; align-items: center; padding-bottom: 14px; border-bottom: 1px solid #ffffff44; }
    .avatar { width: 92px; height: 92px; border-radius: 6px; background: #fff; color: #1d276d; display: grid; place-items: center; font-size: 34px; font-weight: 900; }
    .operator-name { margin-top: 8px; text-align: center; font-size: 14px; font-weight: 800; }
    .quick-top { display: grid; gap: 8px; }
    .quick-top button { min-height: 48px; background: #243979; color: #fff; border: 1px solid #ffffff33; text-align: left; padding: 0 16px; }
    .voice-wrap { display: grid; place-items: center; padding: 20px 0; }
    .voice-button { width: 164px; min-height: 108px; border-radius: 18px; background: #22095f; color: #fff; border: 1px solid #ffffff22; }
    .voice-button .icon { display: block; font-size: 30px; margin-bottom: 6px; }
    .command-menu { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .menu-card { min-height: 106px; padding: 10px 8px; color: #fff; background: #260b68; border: 1px solid #ffffff22; box-shadow: 0 8px 18px #00000024; display: grid; place-items: center; text-align: center; align-content: center; }
    .menu-card .icon { width: 38px; height: 38px; border-radius: 50%; border: 2px solid #fff; display: grid; place-items: center; margin-bottom: 9px; font-size: 13px; }
    .modal-backdrop { position: fixed; inset: 0; z-index: 30; display: none; place-items: end center; padding: 14px; background: #0008; }
    .modal-backdrop.active { display: grid; }
    .modal { width: min(100%, 520px); max-height: 82vh; overflow: auto; background: #fff; color: var(--text); border-radius: 10px; padding: 14px; box-shadow: 0 24px 48px #0007; }
    .modal h2 { margin: 0 0 10px; font-size: 20px; }
    .modal pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f5f8; padding: 10px; border-radius: 6px; font-size: 13px; }
    .primary { background: var(--primary); color: #fff; }
    .secondary { background: #fff; color: var(--text); border: 1px solid var(--line); }
    .danger { background: var(--danger); color: #fff; }
    .ghost { background: transparent; color: #fff; border: 1px solid #ffffff77; }
    .muted { color: var(--muted); font-size: 13px; }
    .error { color: var(--danger); font-weight: 700; }
    .success { color: var(--ok); font-weight: 700; }
    .category-strip { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
    .category-strip button { flex: 0 0 auto; min-width: 116px; padding: 0 14px; background: #fff; color: var(--text); border: 1px solid var(--line); }
    .category-strip button.active { background: var(--primary); color: #fff; border-color: var(--primary); }
    .searchbar { position: sticky; top: 68px; z-index: 9; background: var(--bg); padding-bottom: 10px; }
    .products { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .product-card { min-height: 112px; text-align: left; padding: 12px; background: #fff; border: 1px solid var(--line); color: var(--text); display: grid; align-content: space-between; }
    .product-card strong { font-size: 15px; overflow-wrap: anywhere; }
    .product-card span { color: var(--muted); font-size: 13px; }
    .cart-list { display: grid; gap: 10px; }
    .cart-item { display: grid; grid-template-columns: 1fr auto; gap: 10px; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
    .cart-controls { display: grid; grid-template-columns: 48px 48px; gap: 8px; align-content: start; }
    .cart-controls button { min-height: 44px; }
    .cart-meta { display: flex; gap: 8px; flex-wrap: wrap; color: var(--muted); font-size: 13px; margin-top: 5px; }
    .bottom-bar { position: sticky; bottom: 0; background: #ffffffee; border-top: 1px solid var(--line); padding: 10px 14px; display: grid; gap: 8px; }
    .totals { display: flex; justify-content: space-between; gap: 12px; font-weight: 800; }
    .table-list { width: 100%; border-collapse: collapse; background: #fff; }
    .table-list th, .table-list td { padding: 10px; border-bottom: 1px solid var(--line); text-align: left; font-size: 14px; }
    .table-list th:last-child, .table-list td:last-child { text-align: right; }
    .initial-screen { min-height: calc(100vh - 68px); margin: -14px; padding: 20px 16px 16px; display: grid; grid-template-rows: 1fr auto; color: #fff; background: linear-gradient(160deg, #0f6f8d 0%, #145aa0 48%, #11315e 100%); }
    .brand-hero { display: grid; align-content: center; gap: 18px; text-align: center; }
    .brand-name { font-size: 34px; font-weight: 900; letter-spacing: 0; }
    .brand-visual { width: min(240px, 72vw); aspect-ratio: 1 / .72; margin: 0 auto; border-radius: 22px; background: linear-gradient(145deg, #ffffffee, #d7fbffcc); color: #11456b; display: grid; place-items: center; box-shadow: 0 18px 42px #0000002f; }
    .brand-visual strong { font-size: 54px; line-height: 1; }
    .version-pill { justify-self: center; padding: 8px 14px; border: 1px solid #ffffff66; border-radius: 999px; background: #ffffff18; font-weight: 800; }
    .initial-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .initial-actions button { min-height: 82px; background: #082b54dd; color: #fff; border: 1px solid #ffffff33; display: grid; place-items: center; align-content: center; gap: 6px; }
    .initial-actions .icon { width: 30px; height: 30px; border: 2px solid #fff; border-radius: 50%; display: grid; place-items: center; font-size: 12px; }
    .settings-header { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 10px; margin-bottom: 12px; }
    .settings-list { display: grid; gap: 10px; }
    .settings-section { background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    .settings-section h2 { margin: 0; padding: 12px; font-size: 13px; color: var(--primary-dark); background: #eef6fb; text-transform: uppercase; }
    .setting-row { display: grid; grid-template-columns: 1fr minmax(110px, 42%); gap: 10px; align-items: center; padding: 12px; border-top: 1px solid var(--line); }
    .setting-row strong { display: block; font-size: 15px; }
    .setting-row small { color: var(--muted); }
    .maintenance-bar { position: sticky; bottom: 0; z-index: 12; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; padding: 10px; background: #ffffffee; border: 1px solid var(--line); border-radius: 8px; }
    .maintenance-bar button { min-height: 58px; padding: 6px 4px; background: #123f66; color: #fff; display: grid; place-items: center; align-content: center; gap: 4px; font-size: 11px; }
    .maintenance-bar .icon { width: 24px; height: 24px; border: 1px solid #fff; border-radius: 50%; display: grid; place-items: center; font-size: 10px; }
    .technical-status { display: grid; gap: 8px; }
    .status-line { display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 10px; border: 1px solid var(--line); border-radius: 6px; }
    .status-pill { border-radius: 999px; padding: 4px 8px; font-size: 12px; font-weight: 800; background: #eef3f8; color: var(--text); }
    @media (min-width: 700px) {
      .screen { padding: 18px; }
      .initial-screen { margin: -18px; padding: 28px 24px 20px; }
      .brand-name { font-size: 44px; }
      .initial-actions { max-width: 760px; width: 100%; margin: 0 auto; }
      .initial-actions button { min-height: 110px; font-size: 18px; }
      .menu-screen { margin: -18px; padding: 18px; }
      .actions { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .menu { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .operator-panel { grid-template-columns: 140px 1fr; max-width: 760px; margin: 0 auto; }
      .command-menu { max-width: 760px; margin: 0 auto; gap: 16px; }
      .menu-card { min-height: 128px; }
      .products { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .product-card { min-height: 128px; }
      .bottom-bar { grid-template-columns: 1fr auto; align-items: center; }
    }
    @media (min-width: 1024px) {
      .workspace { display: grid; grid-template-columns: 1fr 380px; gap: 14px; align-items: start; }
      .products { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    }
  </style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div>
      <div id="title" class="title">Movi_commanda</div>
      <div id="subtitle" class="subtitle">Sistema local de comandas</div>
    </div>
    <div id="user-badge" class="user-badge">Sem usuario</div>
  </header>

  <main>
    <section id="screen-initial" class="screen active">
      <div class="initial-screen">
        <div class="brand-hero">
          <div class="brand-name">Movi_commanda</div>
          <div class="brand-visual"><strong>MC</strong></div>
          <div id="app-version" class="version-pill">Versao 1.0.0</div>
        </div>
        <div class="initial-actions">
          <button type="button" onclick="openUsers()"><span class="icon">U</span>USUARIOS</button>
          <button type="button" onclick="openSettings()"><span class="icon">D</span>DEFINICOES</button>
          <button type="button" onclick="startApplication()"><span class="icon">I</span>INICIAR</button>
        </div>
      </div>
    </section>

    <section id="screen-login" class="screen">
      <div class="surface stack">
        <div class="grid">
          <div>
            <label>Token local</label>
            <input id="local-token" type="password" autocomplete="off">
          </div>
          <div>
            <label>Usuario</label>
            <select id="operator-code"></select>
          </div>
          <div>
            <label>Senha</label>
            <input id="operator-password" type="password" autocomplete="current-password">
          </div>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="login()">Entrar</button>
          <button class="secondary" type="button" onclick="loadUsers()">Carregar usuarios</button>
        </div>
        <div id="login-message" class="muted"></div>
      </div>
    </section>

    <section id="screen-settings" class="screen">
      <div class="settings-header">
        <button class="secondary" type="button" onclick="showScreen('initial')">Voltar</button>
        <div>
          <div class="title" style="color:var(--text);">Definicoes</div>
          <div class="muted">Movi_commanda</div>
        </div>
      </div>
      <div class="settings-list">
        <div class="settings-section">
          <h2>Servidor</h2>
          <div class="setting-row"><div><strong>Smart Connect</strong><small>Conexao local configuravel</small></div><button class="secondary" type="button" onclick="testConnection()">Testar</button></div>
          <div class="setting-row"><div><strong>Endereco IP</strong><small>Servidor local ou remoto</small></div><input id="set-ip-servidor"></div>
          <div class="setting-row"><div><strong>Licenca</strong><small>Codigo de licenca</small></div><input id="set-licenca"></div>
          <div class="setting-row"><div><strong>Porta</strong><small>Porta da API</small></div><input id="set-porta-servidor" type="number" min="1" max="65535"></div>
          <div class="setting-row"><div><strong>Nome da(s) rede(s) Wi-Fi</strong><small>SSID permitido</small></div><input id="set-ssid-wifi"></div>
          <div class="setting-row"><div><strong>IP local automatico</strong><small>Endereco para celulares/tablets</small></div><select id="set-local-ip"></select></div>
          <div class="setting-row"><div><strong>URL de conexao</strong><small id="local-access-url">Carregando rede local</small></div><button class="secondary" type="button" onclick="copyConnectionUrl()">Copiar</button></div>
          <div class="setting-row"><div><strong>Token de pareamento</strong><small>Codigo curto para conectar celulares/tablets</small></div><button class="primary" type="button" onclick="generatePairingToken()">Gerar token</button></div>
          <div class="setting-row"><div><strong>Carregar dados</strong><small>Atualiza usuarios, familias e produtos</small></div><button class="primary" type="button" onclick="loadServerData()">Carregar dados</button></div>
        </div>
        <div class="settings-section">
          <h2>Status tecnico</h2>
          <div id="technical-status" class="technical-status" style="padding:12px;">
            <div class="muted">Use os botoes inferiores para verificar conexoes e dispositivos.</div>
          </div>
        </div>
        <div class="settings-section">
          <h2>Impressora Bluetooth</h2>
          <div class="setting-row"><div><strong>Selecione a impressora</strong><small>Nome da impressora local</small></div><input id="set-impressora-bluetooth"></div>
          <div class="setting-row"><div><strong>DPI da impressora</strong></div><input id="set-dpi-impressora" type="number" min="72" max="600"></div>
          <div class="setting-row"><div><strong>Largura da impressora</strong></div><input id="set-largura-impressora" type="number" min="20" max="120"></div>
          <div class="setting-row"><div><strong>Caracteres por linha</strong></div><input id="set-caracteres-por-linha" type="number" min="16" max="80"></div>
        </div>
        <div class="settings-section">
          <h2>Outras configuracoes</h2>
          <div class="setting-row"><div><strong>Nomenclatura exibida</strong><small>Altera apenas textos e impressao</small></div><select id="set-nomenclatura-mesa"><option value="Mesa">Mesa</option><option value="Comanda">Comanda</option></select></div>
          <div class="setting-row"><div><strong>Interface</strong><small>Tema visual</small></div><input id="set-tema-interface"></div>
          <div class="setting-row"><div><strong>Aplicativo</strong><small>Usuario logado</small></div><input id="set-usuario-logado"></div>
        </div>
        <div class="settings-section">
          <h2>Ajuda</h2>
          <div class="setting-row"><div><strong>Pagina oficial</strong><small>movisystecnologia.com.br</small></div><button class="secondary" type="button" onclick="window.open('https://movisystecnologia.com.br','_blank')">Abrir</button></div>
          <div class="setting-row"><div><strong>Fale conosco</strong><small>Suporte MoviSys</small></div><button class="secondary" type="button" onclick="openModal('Fale conosco', '<pre>Entre em contato com o suporte MoviSys.</pre>')">Abrir</button></div>
        </div>
        <div class="settings-section">
          <h2>Sobre</h2>
          <div class="setting-row"><div><strong>Sobre a aplicacao</strong><small>Sistema mobile de comandas</small></div><span>Movi_commanda</span></div>
          <div class="setting-row"><div><strong>Nome da versao</strong></div><input id="set-versao-app"></div>
          <div class="setting-row"><div><strong>Codigo da versao</strong></div><input id="set-codigo-versao"></div>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="saveSettings()">Salvar definicoes</button>
          <button class="secondary" type="button" onclick="validateLicense()">Validar licenca</button>
        </div>
        <div class="maintenance-bar">
          <button type="button" onclick="restartService()"><span class="icon">R</span>Reiniciar</button>
          <button type="button" onclick="checkConnections()"><span class="icon">C</span>Conexao</button>
          <button type="button" onclick="showConnectedClients()"><span class="icon">D</span>Clientes</button>
          <button type="button" onclick="showConnectionIp()"><span class="icon">IP</span>IP</button>
          <button type="button" onclick="openDatabasePanel()"><span class="icon">DB</span>Banco</button>
        </div>
        <div id="settings-message" class="muted"></div>
      </div>
    </section>

    <section id="screen-menu" class="screen">
      <div class="menu-screen">
        <div class="operator-panel">
          <div>
            <div class="avatar" id="operator-avatar">OP</div>
            <div class="operator-name" id="operator-name">SUPORTE</div>
          </div>
          <div class="quick-top">
            <button type="button" onclick="openOutbox()">CAIXA DE SAIDA</button>
            <button type="button" onclick="openMessages()">MENSAGENS</button>
          </div>
        </div>
        <div class="voice-wrap">
          <button class="voice-button" type="button" onclick="startVoiceCommand()">
            <span class="icon">MIC</span>
            CONTROLE POR VOZ
          </button>
        </div>
        <div class="command-menu">
          <button class="menu-card" type="button" onclick="startOrder()"><span class="icon">P</span>PEDIR</button>
          <button class="menu-card" type="button" onclick="openVoidFlow()"><span class="icon">X</span>ANULAR</button>
          <button class="menu-card" type="button" onclick="openSubtotalFlow()"><span class="icon">S</span>SUBTOTAL</button>
          <button class="menu-card" type="button" onclick="openAccountFlow()"><span class="icon">FC</span>FECHAR CONTA</button>
          <button class="menu-card" type="button" onclick="openTransferFlow()"><span class="icon">TR</span>TRANSFERENCIA</button>
          <button class="menu-card" type="button" onclick="openPartialPaymentFlow()"><span class="icon">PP</span>PAGAMENTO PARCIAL</button>
          <button class="menu-card" type="button" onclick="openOtherMenu()"><span class="icon">...</span>OUTROS</button>
          <button class="menu-card" type="button" onclick="openDiscountFlow()"><span class="icon">%</span>DESCONTO</button>
          <button class="menu-card" type="button" onclick="goInitialMenu()"><span class="icon">IN</span>MENU INICIAL</button>
        </div>
      </div>
    </section>

    <section id="screen-start" class="screen">
      <div class="surface stack">
        <div class="grid two">
          <div>
            <label data-table-label>Mesa</label>
            <input id="command-number" inputmode="numeric" autocomplete="off">
          </div>
          <div>
            <label>Quantidade de pessoas</label>
            <input id="people-count" type="number" min="1" step="1" inputmode="numeric">
          </div>
          <div>
            <label>Referencia</label>
            <input id="table-reference" autocomplete="off">
          </div>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="goProducts()">Selecionar produtos</button>
          <button class="secondary" type="button" onclick="showScreen('menu')">Voltar</button>
        </div>
        <div id="table-label-help" class="muted">Mesa identifica o pedido. Referencia e apenas apoio operacional.</div>
      </div>
    </section>

    <section id="screen-products" class="screen">
      <div class="workspace">
        <div class="stack">
          <div class="searchbar">
            <label>Buscar produto</label>
            <input id="product-search" placeholder="Nome ou codigo" oninput="searchProductsDebounced()">
          </div>
          <div id="families" class="category-strip"></div>
          <div id="products" class="products"></div>
        </div>
        <div class="surface stack">
          <div class="totals"><span>Carrinho</span><span id="cart-count">0 itens</span></div>
          <div id="mini-cart" class="cart-list"></div>
          <button class="primary" type="button" onclick="showReview()">Revisar pedido</button>
        </div>
      </div>
    </section>

    <section id="screen-review" class="screen">
      <div class="stack">
        <div class="surface">
          <div class="totals">
            <span id="review-header">Pedido</span>
            <span id="review-total">R$ 0,00</span>
          </div>
          <div class="muted" id="review-meta"></div>
        </div>
        <div id="cart-list" class="cart-list"></div>
        <div class="bottom-bar">
          <div class="totals"><span id="total-items">0 itens</span><span id="total-amount">R$ 0,00</span></div>
          <div class="actions">
            <button class="danger" type="button" onclick="clearCart()">Lixeira</button>
            <button class="secondary" type="button" onclick="showScreen('products')">Adicionar mais</button>
            <button class="primary" type="button" onclick="confirmOrder()">Confirmar pedido</button>
          </div>
        </div>
      </div>
    </section>

    <section id="screen-consult" class="screen">
      <div class="surface stack">
        <div class="grid two">
          <div>
            <label>Referencia</label>
            <input id="consult-table" autocomplete="off">
          </div>
          <div>
            <label data-table-label>Mesa</label>
            <input id="consult-command" autocomplete="off">
          </div>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="loadOrders()">Consultar</button>
          <button class="secondary" type="button" onclick="showScreen('menu')">Voltar</button>
        </div>
      </div>
      <div class="surface" style="margin-top:12px; overflow:auto;">
        <table class="table-list">
          <thead><tr><th data-table-label>Mesa</th><th>Referencia</th><th>Status</th><th>Total</th><th></th></tr></thead>
          <tbody id="orders"></tbody>
        </table>
      </div>
    </section>

    <section id="screen-print" class="screen">
      <div class="surface stack">
        <div>
          <label><span data-table-label>Mesa</span> para pre-conta</label>
          <select id="print-order"></select>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="printPrebill()">Imprimir pre-conta</button>
          <button class="secondary" type="button" onclick="showScreen('menu')">Voltar</button>
        </div>
        <div id="system-message" class="muted"></div>
      </div>
    </section>
  </main>
</div>
<div id="modal-backdrop" class="modal-backdrop">
  <div class="modal">
    <h2 id="modal-title">Operacao</h2>
    <div id="modal-body" class="stack"></div>
    <div class="actions" style="margin-top:12px;">
      <button class="secondary" type="button" onclick="closeModal()">Fechar</button>
    </div>
  </div>
</div>

<script>
const state = {
  sessionToken: '',
  operator: null,
  families: [],
  products: [],
  selectedFamily: '',
  cart: [],
  permissions: {},
  activeOrderUuid: '',
  activeCommandNumber: '',
  networkInfo: null,
  searchTimer: null,
  tableLabel: 'Mesa'
};

function localHeaders(json = true) {
  const headers = {};
  const token = document.getElementById('local-token').value.trim();
  if (json) headers['Content-Type'] = 'application/json';
  if (token) headers['X-Local-Token'] = token;
  if (state.sessionToken) headers['X-Order-Session'] = state.sessionToken;
  return headers;
}

function showScreen(name) {
  for (const screen of document.querySelectorAll('.screen')) screen.classList.remove('active');
  document.getElementById(`screen-${name}`).classList.add('active');
  document.getElementById('title').textContent = {
    initial: 'Movi_commanda',
    login: 'Usuarios',
    settings: 'Definicoes',
    menu: 'Menu principal',
    start: 'Novo pedido',
    products: 'Selecionar produtos',
    review: 'Revisar pedido',
    consult: 'Consultar comanda',
    print: 'Imprimir pre-conta'
  }[name];
  document.getElementById('subtitle').textContent = name === 'initial' ? 'Sistema local de comandas' : 'Movi_commanda';
}

function money(value) {
  return Number(value || 0).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function tableLabel() {
  return state.tableLabel;
}

function applyTableLabel(value) {
  state.tableLabel = value === 'Comanda' ? 'Comanda' : 'Mesa';
  document.querySelectorAll('[data-table-label]').forEach(el => {
    el.textContent = state.tableLabel;
  });
  const help = document.getElementById('table-label-help');
  if (help) help.textContent = `${state.tableLabel} identifica o pedido. Referencia e apenas apoio operacional.`;
}

async function responseMessage(response) {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    if (data.detail === 'Local token invalid.') return 'Token local invalido. No servidor, abra por http://127.0.0.1:8765/orders/ui para preencher automaticamente. No celular, copie o token de ACESSO_REDE_LOCAL.txt.';
    if (data.detail === 'Sessao de usuario obrigatoria.') return 'Entre em USUARIOS com operador tecnico antes de usar esta funcao.';
    if (data.detail === 'Sessao de usuario invalida ou expirada.') return 'Sessao expirada. Entre novamente em USUARIOS.';
    return data.detail || data.message || text;
  } catch {
    return text;
  }
}

async function loadUsers() {
  const message = document.getElementById('login-message');
  const select = document.getElementById('operator-code');
  message.textContent = 'Carregando usuarios...';
  const response = await localFetch('/orders/users', {headers: localHeaders(false)});
  if (!response.ok) {
    message.className = 'error';
    message.textContent = 'Nao foi possivel carregar usuarios. Verifique token local e banco.';
    return;
  }
  const data = await response.json();
  select.innerHTML = data.operators.map(user => `<option value="${escapeHtml(user.code)}">${escapeHtml(user.name)}</option>`).join('');
  message.className = 'muted';
  message.textContent = data.operators.length ? 'Usuarios carregados.' : 'Nenhum usuario ativo encontrado.';
}

async function loadAppInfo() {
  const response = await localFetch('/orders/app-info', {headers: localHeaders(false)});
  if (!response.ok) return;
  const data = await response.json();
  document.getElementById('app-version').textContent = `Versao ${data.version_name}`;
}

function isLoopbackHost() {
  return ['127.0.0.1', 'localhost', '::1'].includes(window.location.hostname);
}

async function loadLocalTokenIfAvailable(force = false) {
  const tokenInput = document.getElementById('local-token');
  if (tokenInput.value.trim() && !force) return false;
  if (!isLoopbackHost()) return false;
  const response = await window.fetch('/orders/local-token');
  if (!response.ok) return false;
  const data = await response.json();
  tokenInput.value = data.token || '';
  return Boolean(tokenInput.value.trim());
}

async function localFetch(url, options = {}, retried = false) {
  const response = await window.fetch(url, options);
  if (response.status !== 401 || retried || !isLoopbackHost()) return response;
  let data = null;
  try {
    data = await response.clone().json();
  } catch {
    return response;
  }
  if (data.detail !== 'Local token invalid.') return response;
  const refreshed = await loadLocalTokenIfAvailable(true);
  if (!refreshed) return response;
  const nextOptions = {...options, headers: localHeaders(options.headers?.['Content-Type'] !== undefined)};
  return localFetch(url, nextOptions, true);
}

async function openUsers() {
  await loadLocalTokenIfAvailable();
  await loadUsers();
  showScreen('login');
}

function startApplication() {
  if (state.sessionToken && state.operator) {
    showScreen('menu');
    return;
  }
  openUsers();
}

async function requireTechnicalSession() {
  if (state.sessionToken && state.operator) return true;
  await loadLocalTokenIfAvailable();
  openModal(
    'Login tecnico',
    '<pre>Entre em USUARIOS com operador tecnico para usar esta funcao.</pre><button class="primary" type="button" onclick="closeModal(); openUsers()">Entrar</button>'
  );
  return false;
}

function hasPermission(permission) {
  return state.permissions[permission] !== false;
}

async function openSettings() {
  await loadLocalTokenIfAvailable();
  await loadSettings();
  await loadNetworkInfo();
  showScreen('settings');
}

function settingsPayload() {
  return {
    ip_servidor: document.getElementById('set-ip-servidor').value,
    porta_servidor: document.getElementById('set-porta-servidor').value || null,
    licenca: document.getElementById('set-licenca').value,
    ssid_wifi: document.getElementById('set-ssid-wifi').value,
    impressora_bluetooth: document.getElementById('set-impressora-bluetooth').value,
    dpi_impressora: document.getElementById('set-dpi-impressora').value || null,
    largura_impressora: document.getElementById('set-largura-impressora').value || null,
    caracteres_por_linha: document.getElementById('set-caracteres-por-linha').value || null,
    tema_interface: document.getElementById('set-tema-interface').value,
    usuario_logado: document.getElementById('set-usuario-logado').value,
    versao_app: document.getElementById('set-versao-app').value,
    codigo_versao: document.getElementById('set-codigo-versao').value,
    nomenclatura_mesa: document.getElementById('set-nomenclatura-mesa').value
  };
}

function fillSettings(settings) {
  document.getElementById('set-ip-servidor').value = settings.ip_servidor || '';
  document.getElementById('set-porta-servidor').value = settings.porta_servidor || '';
  document.getElementById('set-licenca').value = settings.licenca || '';
  document.getElementById('set-ssid-wifi').value = settings.ssid_wifi || '';
  document.getElementById('set-impressora-bluetooth').value = settings.impressora_bluetooth || '';
  document.getElementById('set-dpi-impressora').value = settings.dpi_impressora || 203;
  document.getElementById('set-largura-impressora').value = settings.largura_impressora || 58;
  document.getElementById('set-caracteres-por-linha').value = settings.caracteres_por_linha || 32;
  document.getElementById('set-tema-interface').value = settings.tema_interface || 'padrao';
  document.getElementById('set-usuario-logado').value = settings.usuario_logado || '';
  document.getElementById('set-versao-app').value = settings.versao_app || '';
  document.getElementById('set-codigo-versao').value = settings.codigo_versao || '';
  document.getElementById('set-nomenclatura-mesa').value = settings.nomenclatura_mesa || 'Mesa';
  applyTableLabel(settings.nomenclatura_mesa || 'Mesa');
}

async function loadNetworkInfo() {
  const response = await localFetch('/orders/technical/network', {headers: localHeaders(false)});
  if (!response.ok) return;
  const data = await response.json();
  state.networkInfo = data;
  const select = document.getElementById('set-local-ip');
  const addresses = data.addresses || [];
  select.innerHTML = addresses.map(item => `<option value="${escapeHtml(item.ip)}" ${item.selected ? 'selected' : ''}>${escapeHtml(item.ip)} - ${escapeHtml(item.label)}</option>`).join('');
  const selected = addresses.find(item => item.ip === select.value) || addresses[0];
  document.getElementById('local-access-url').textContent = selected ? selected.url : 'Nenhum IP local encontrado';
}

function selectedAccessUrl() {
  const select = document.getElementById('set-local-ip');
  const addresses = state.networkInfo?.addresses || [];
  const selected = addresses.find(item => item.ip === select.value) || addresses[0];
  return selected ? selected.url : '';
}

async function copyConnectionUrl() {
  const url = selectedAccessUrl();
  if (!url) return;
  await navigator.clipboard?.writeText(url);
  document.getElementById('settings-message').className = 'success';
  document.getElementById('settings-message').textContent = 'Endereco copiado.';
}

async function generatePairingToken() {
  const response = await localFetch('/orders/pairing/token', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await responseMessage(response)};
  if (!response.ok) {
    openModal('Token de pareamento', `<pre>${escapeHtml(data.message)}</pre>`);
    return;
  }
  document.getElementById('local-token').value = data.token;
  openModal('Token de pareamento', `
    <pre>${escapeHtml(`Token: ${data.token}\nURL: ${data.url}\nDigite este codigo no celular para parear.`)}</pre>
    <button class="primary" type="button" onclick="navigator.clipboard?.writeText('${escapeHtml(data.token)}')">Copiar token</button>
  `);
}

async function loadSettings() {
  const message = document.getElementById('settings-message');
  const response = await localFetch('/orders/settings', {headers: localHeaders(false)});
  if (!response.ok) {
    if (message) message.textContent = 'Nao foi possivel carregar definicoes. Verifique token local.';
    return;
  }
  const data = await response.json();
  fillSettings(data.settings);
}

async function saveSettings() {
  const message = document.getElementById('settings-message');
  const payload = settingsPayload();
  if (!payload.ip_servidor || !payload.porta_servidor) {
    message.className = 'error';
    message.textContent = 'Endereco IP e porta sao obrigatorios.';
    return;
  }
  const response = await localFetch('/orders/settings', {
    method: 'PUT',
    headers: localHeaders(),
    body: JSON.stringify(payload)
  });
  message.className = response.ok ? 'success' : 'error';
  message.textContent = response.ok ? 'Definicoes salvas.' : await response.text();
  if (response.ok) applyTableLabel(payload.nomenclatura_mesa);
}

async function testConnection() {
  const response = await localFetch('/orders/settings/test-connection', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Smart Connect', `<pre>${escapeHtml(data.message)}</pre>`);
}

async function loadServerData() {
  const response = await localFetch('/orders/settings/load-server-data', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Carregar dados', `<pre>${escapeHtml(data.message)}</pre>`);
}

async function validateLicense() {
  const response = await localFetch('/orders/license/validate', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Licenca', `<pre>${escapeHtml(data.message)}</pre>`);
}

function renderStatusLines(payload) {
  return `<div class="technical-status">
    ${Object.entries(payload).map(([key, value]) => `
      <div class="status-line">
        <div><strong>${escapeHtml(key)}</strong><div class="muted">${escapeHtml(value.message || '')}</div></div>
        <span class="status-pill">${escapeHtml(value.status || '')}</span>
      </div>
    `).join('')}
  </div>`;
}

async function restartService() {
  if (!(await requireTechnicalSession())) return;
  const response = await localFetch('/orders/technical/restart-service', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {status: 'error', message: await responseMessage(response)};
  openModal('Reiniciar servico', `<pre>${escapeHtml(data.message)}</pre>`);
}

async function checkConnections() {
  if (!(await requireTechnicalSession())) return;
  const response = await localFetch('/orders/technical/check', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await responseMessage(response)};
  if (!response.ok) {
    openModal('Verificar conexao', `<pre>${escapeHtml(data.message)}</pre>`);
    return;
  }
  document.getElementById('technical-status').innerHTML = renderStatusLines({
    API: data.server_api,
    Banco: data.database,
    Impressora: data.printer
  });
  openModal('Verificar conexao', renderStatusLines({
    API: data.server_api,
    Banco: data.database,
    Impressora: data.printer
  }));
}

async function showConnectedClients() {
  if (!(await requireTechnicalSession())) return;
  const response = await localFetch('/orders/technical/clients', {headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {clients: [], message: await responseMessage(response)};
  if (!response.ok) {
    openModal('Clientes conectados', `<pre>${escapeHtml(data.message)}</pre>`);
    return;
  }
  const rows = data.clients.map(client => `
    <div class="surface">
      <strong>${escapeHtml(client.ip)}</strong>
      <div class="muted">${escapeHtml(client.operator_name || client.operator_code || 'Sem usuario')} | ${escapeHtml(client.status)} | ${escapeHtml(client.last_seen_at)}</div>
      <div class="muted">${escapeHtml(client.device_name || client.user_agent || 'Dispositivo sem nome')}</div>
    </div>
  `).join('');
  openModal('Clientes conectados', rows || '<div class="muted">Nenhum cliente conectado.</div>');
}

async function showConnectionIp() {
  await loadNetworkInfo();
  const url = selectedAccessUrl();
  openModal('IP de conexao', `
    <pre>${escapeHtml(`IP: ${document.getElementById('set-local-ip').value || 'nao detectado'}\nPorta: ${state.networkInfo?.port || ''}\nURL: ${url}`)}</pre>
    <button class="primary" type="button" onclick="copyConnectionUrl()">Copiar endereco</button>
  `);
}

async function openDatabasePanel() {
  if (!(await requireTechnicalSession())) return;
  const response = await localFetch('/orders/technical/database', {headers: localHeaders(false)});
  if (!response.ok) {
    openModal('Banco de dados', `<pre>${escapeHtml(await responseMessage(response))}</pre>`);
    return;
  }
  const config = await response.json();
  openModal('Banco de dados', `
    <div class="grid two">
      <div><label>Tipo de banco</label><input id="db-type" value="${escapeHtml(config.database_type || 'mariadb')}"></div>
      <div><label>Host/IP</label><input id="db-host" value="${escapeHtml(config.host || '')}"></div>
      <div><label>Porta</label><input id="db-port" type="number" value="${escapeHtml(config.port || 3308)}"></div>
      <div><label>Nome do banco</label><input id="db-name" value="${escapeHtml(config.database || '')}"></div>
      <div><label>Usuario</label><input id="db-user" value="${escapeHtml(config.username || '')}"></div>
      <div><label>Senha</label><input id="db-pass" type="password" placeholder="${config.password_configured ? 'Senha configurada' : ''}"></div>
    </div>
    <div class="actions">
      <button class="secondary" type="button" onclick="testDatabaseConnection()">Testar conexao</button>
      <button class="primary" type="button" onclick="saveDatabaseConfig()">Salvar configuracao</button>
    </div>
    <div id="db-message" class="muted"></div>
  `);
}

function databasePayload() {
  return {
    database_type: document.getElementById('db-type').value,
    host: document.getElementById('db-host').value,
    port: Number(document.getElementById('db-port').value || 0),
    database: document.getElementById('db-name').value,
    username: document.getElementById('db-user').value,
    password: document.getElementById('db-pass').value || null,
    ssl_enabled: false
  };
}

async function testDatabaseConnection() {
  const response = await localFetch('/orders/technical/database/test', {method: 'POST', headers: localHeaders(), body: JSON.stringify(databasePayload())});
  const data = response.ok ? await response.json() : {message: await responseMessage(response)};
  document.getElementById('db-message').className = response.ok && data.status === 'connected' ? 'success' : 'error';
  document.getElementById('db-message').textContent = data.message;
}

async function saveDatabaseConfig() {
  const payload = databasePayload();
  if (!payload.host || !payload.port || !payload.database || !payload.username) {
    document.getElementById('db-message').className = 'error';
    document.getElementById('db-message').textContent = 'Host, porta, banco e usuario sao obrigatorios.';
    return;
  }
  const response = await localFetch('/orders/technical/database', {method: 'PUT', headers: localHeaders(), body: JSON.stringify(payload)});
  document.getElementById('db-message').className = response.ok ? 'success' : 'error';
  document.getElementById('db-message').textContent = response.ok ? 'Configuracao salva.' : await responseMessage(response);
}

async function login() {
  const message = document.getElementById('login-message');
  const payload = {
    operator_code: document.getElementById('operator-code').value,
    password: document.getElementById('operator-password').value
  };
  const response = await localFetch('/orders/login', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    message.className = 'error';
    message.textContent = 'Usuario ou senha invalido.';
    return;
  }
  const data = await response.json();
  state.sessionToken = data.session_token;
  state.operator = data.operator;
  const meResponse = await localFetch('/orders/me', {headers: localHeaders(false)});
  state.permissions = meResponse.ok ? (await meResponse.json()).permissions || {} : {};
  document.getElementById('user-badge').textContent = data.operator.name;
  document.getElementById('operator-name').textContent = data.operator.name || 'SUPORTE';
  document.getElementById('operator-avatar').textContent = (data.operator.name || data.operator.code || 'OP').slice(0, 2).toUpperCase();
  message.className = 'success';
  message.textContent = 'Login autorizado.';
  await loadFamilies();
  showScreen('menu');
}

function logout() {
  state.sessionToken = '';
  state.operator = null;
  state.permissions = {};
  state.cart = [];
  state.activeOrderUuid = '';
  state.activeCommandNumber = '';
  document.getElementById('operator-password').value = '';
  document.getElementById('user-badge').textContent = 'Sem usuario';
  renderCart();
  showScreen('login');
}

function startOrder() {
  state.cart = [];
  renderCart();
  document.getElementById('command-number').value = '';
  document.getElementById('people-count').value = '';
  document.getElementById('table-reference').value = '';
  showScreen('start');
}

async function goProducts() {
  const command = document.getElementById('command-number').value.trim();
  const table = document.getElementById('table-reference').value.trim();
  if (!command) {
    alert(`Informe a ${tableLabel().toLowerCase()}.`);
    return;
  }
  await loadProducts();
  showScreen('products');
}

async function loadFamilies() {
  const response = await localFetch('/orders/product-families', {headers: localHeaders(false)});
  if (!response.ok) return;
  const data = await response.json();
  state.families = data.families;
  state.selectedFamily = data.families[0] || '';
  renderFamilies();
}

function renderFamilies() {
  const el = document.getElementById('families');
  el.innerHTML = state.families.map((family, index) => `
    <button type="button" class="${family === state.selectedFamily ? 'active' : ''}" onclick="selectFamilyByIndex(${index})">${escapeHtml(family)}</button>
  `).join('');
}

async function selectFamilyByIndex(index) {
  await selectFamily(state.families[index] || '');
}

async function selectFamily(family) {
  state.selectedFamily = family;
  renderFamilies();
  await loadProducts();
}

function searchProductsDebounced() {
  window.clearTimeout(state.searchTimer);
  state.searchTimer = window.setTimeout(loadProducts, 250);
}

async function loadProducts() {
  const q = document.getElementById('product-search').value.trim();
  const params = new URLSearchParams();
  if (state.selectedFamily && !q) params.set('family', state.selectedFamily);
  if (q) params.set('q', q);
  const response = await localFetch(`/orders/products?${params.toString()}`, {headers: localHeaders(false)});
  if (!response.ok) return;
  const data = await response.json();
  state.products = data.products;
  document.getElementById('products').innerHTML = data.products.map((product, index) => `
    <button class="product-card" type="button" onclick="addProductByIndex(${index})">
      <strong>${escapeHtml(product.description)}</strong>
      <span>${escapeHtml(product.product_code)} - ${money(product.unit_price)}</span>
    </button>
  `).join('');
}

function addProductByIndex(index) {
  const product = state.products[index];
  if (product) addProduct(product);
}

function addProduct(product) {
  const existing = state.cart.find(item => item.product_code === product.product_code && !item.notes);
  if (existing) existing.quantity = Number(existing.quantity) + 1;
  else state.cart.push({...product, quantity: 1, notes: ''});
  renderCart();
}

function setQuantity(index, delta) {
  const item = state.cart[index];
  item.quantity = Math.max(1, Number(item.quantity) + delta);
  renderCart();
}

function removeCartItem(index) {
  state.cart.splice(index, 1);
  renderCart();
}

function editNotes(index) {
  const notes = prompt('Observacao do item', state.cart[index].notes || '');
  if (notes === null) return;
  state.cart[index].notes = notes.trim();
  renderCart();
}

function clearCart() {
  state.cart = [];
  renderCart();
}

function totals() {
  const count = state.cart.reduce((sum, item) => sum + Number(item.quantity), 0);
  const amount = state.cart.reduce((sum, item) => sum + Number(item.quantity) * Number(item.unit_price), 0);
  return {count, amount};
}

function renderCart() {
  const {count, amount} = totals();
  document.getElementById('cart-count').textContent = `${count} itens`;
  document.getElementById('mini-cart').innerHTML = state.cart.slice(0, 5).map(item => `
    <div class="muted">${escapeHtml(item.quantity)}x ${escapeHtml(item.description)}</div>
  `).join('');
  document.getElementById('cart-list').innerHTML = state.cart.map((item, index) => `
    <div class="cart-item">
      <div>
        <strong>${escapeHtml(item.description)}</strong>
        <div class="cart-meta">
          <span>${escapeHtml(item.product_code)}</span>
          <span>${money(item.unit_price)}</span>
          <span>${money(Number(item.quantity) * Number(item.unit_price))}</span>
        </div>
        <button class="secondary" type="button" onclick="editNotes(${index})">${escapeHtml(item.notes || 'Adicionar observacao')}</button>
      </div>
      <div class="cart-controls">
        <button class="secondary" type="button" onclick="setQuantity(${index}, 1)">+</button>
        <button class="secondary" type="button" onclick="setQuantity(${index}, -1)">-</button>
        <button class="danger" type="button" onclick="removeCartItem(${index})">X</button>
      </div>
    </div>
  `).join('');
  document.getElementById('total-items').textContent = `${count} itens`;
  document.getElementById('total-amount').textContent = money(amount);
  document.getElementById('review-total').textContent = money(amount);
}

function showReview() {
  if (!state.cart.length) {
    alert('Adicione ao menos um produto.');
    return;
  }
  const command = document.getElementById('command-number').value.trim();
  const table = document.getElementById('table-reference').value.trim();
  document.getElementById('review-header').textContent = `${tableLabel()} ${command}`;
  document.getElementById('review-meta').textContent = `Referencia ${table || '-'} | Pessoas ${document.getElementById('people-count').value || '-'}`;
  renderCart();
  showScreen('review');
}

async function confirmOrder() {
  if (!state.cart.length) {
    alert('Pedido vazio.');
    return;
  }
  const payload = {
    command_number: document.getElementById('command-number').value.trim(),
    people_count: document.getElementById('people-count').value || null,
    table_reference: document.getElementById('table-reference').value.trim() || null,
    operator_code: state.operator ? state.operator.code : null,
    items: state.cart.map(item => ({
      product_code: item.product_code,
      description: item.description,
      quantity: String(item.quantity),
      unit_price: String(item.unit_price),
      notes: item.notes || null
    }))
  };
  const response = await localFetch('/orders/confirm', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    alert(await response.text());
    return;
  }
  const saved = await response.json();
  state.activeOrderUuid = saved.uuid;
  state.activeCommandNumber = saved.command_number;
  state.cart = [];
  renderCart();
  await loadOrders();
  showScreen('menu');
}

function openConsult() {
  loadOrders();
  showScreen('consult');
}

function openPrint() {
  loadOrders();
  showScreen('print');
}

async function loadOrders() {
  const table = document.getElementById('consult-table').value.trim();
  const command = document.getElementById('consult-command').value.trim();
  const url = table ? `/orders?table_reference=${encodeURIComponent(table)}` : '/orders';
  const response = await localFetch(url, {headers: localHeaders(false)});
  if (!response.ok) return;
  const data = await response.json();
  const orders = command ? data.orders.filter(order => order.command_number === command) : data.orders;
  document.getElementById('orders').innerHTML = orders.map(order => `
    <tr>
      <td>${escapeHtml(order.command_number)}</td>
      <td>${escapeHtml(order.table_reference || '')}</td>
      <td>${escapeHtml(order.status)}</td>
      <td>${money(order.total_amount)}</td>
      <td><button class="secondary" type="button" onclick="window.open('/orders/${order.uuid}/prebill','_blank')">Pre-conta</button></td>
    </tr>
  `).join('');
  document.getElementById('print-order').innerHTML = orders.map(order => `
    <option value="${escapeHtml(order.uuid)}">${tableLabel()} ${escapeHtml(order.command_number)} - Ref ${escapeHtml(order.table_reference || '-')}</option>
  `).join('');
}

function openModal(title, html) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-backdrop').classList.add('active');
}

function closeModal() {
  document.getElementById('modal-backdrop').classList.remove('active');
}

function activeCommand() {
  return state.activeCommandNumber || document.getElementById('command-number').value.trim() || prompt(`Numero da ${tableLabel().toLowerCase()}`) || '';
}

function renderSummary(payload) {
  if (!payload || !payload.order) return '<div class="muted">Sem dados.</div>';
  const order = payload.order;
  const items = (order.items || []).map(item => `
    <tr>
      <td>${escapeHtml(item.description)}</td>
      <td>${escapeHtml(item.quantity)}</td>
      <td>${money(item.unit_price)}</td>
      <td>${money(item.line_total)}</td>
    </tr>
  `).join('');
  return `
    <div class="muted">${tableLabel()} ${escapeHtml(order.command_number)} | Referencia ${escapeHtml(order.table_reference || '-')} | Pessoas ${escapeHtml(order.people_count || '-')}</div>
    <table class="table-list">
      <thead><tr><th>Item</th><th>Qtd</th><th>Unit.</th><th>Total</th></tr></thead>
      <tbody>${items}</tbody>
    </table>
    <div class="totals"><span>Subtotal</span><span>${money(payload.subtotal)}</span></div>
    <div class="totals"><span>Descontos</span><span>${money(payload.discounts)}</span></div>
    <div class="totals"><span>Pagamentos parciais</span><span>${money(payload.partial_payments)}</span></div>
    <div class="totals"><span>Total final</span><span>${money(payload.total)}</span></div>
    <div class="totals"><span>Saldo restante</span><span>${money(payload.remaining)}</span></div>
    <button class="primary" type="button" onclick="window.open('/orders/${order.uuid}/prebill','_blank')">Imprimir pre-conta</button>
  `;
}

async function openSubtotalFlow() {
  const command = activeCommand();
  if (!command) return;
  const response = await localFetch(`/orders/subtotal?command_number=${encodeURIComponent(command)}`, {headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Subtotal', response.ok ? renderSummary(data.payload) : `<pre>${escapeHtml(data.message)}</pre>`);
}

async function openAccountFlow() {
  if (!hasPermission('order.close')) {
    openModal('Fechar conta', '<pre>Nao tem permissao para fechar conta.</pre>');
    return;
  }
  const command = activeCommand();
  if (!command) return;
  const response = await localFetch(`/orders/account?command_number=${encodeURIComponent(command)}`, {headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await responseMessage(response)};
  openModal('Fechar conta', response.ok ? renderSummary(data.payload) : `<pre>${escapeHtml(data.message)}</pre>`);
}

async function openVoidFlow() {
  const command = activeCommand();
  const reason = prompt('Motivo da anulacao');
  if (!command || !reason) return;
  const response = await localFetch('/orders/void', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify({command_number: command, reason})
  });
  const text = response.ok ? 'Anulacao registrada.' : await response.text();
  openModal('Anular', `<pre>${escapeHtml(text)}</pre>`);
  await loadOrders();
}

async function openTransferFlow() {
  const source = activeCommand();
  const destinationTable = prompt('Referencia destino');
  const reason = prompt('Motivo da transferencia');
  if (!source || !destinationTable || !reason) return;
  const response = await localFetch('/orders/transfer', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify({
      transfer_type: 'table',
      source_command_number: source,
      destination_table_reference: destinationTable,
      reason
    })
  });
  const text = response.ok ? 'Transferencia registrada.' : await response.text();
  openModal('Transferencia', `<pre>${escapeHtml(text)}</pre>`);
  await loadOrders();
}

async function openPartialPaymentFlow() {
  const command = activeCommand();
  const amount = prompt('Valor do pagamento parcial');
  const paymentMethod = prompt('Forma de pagamento');
  if (!command || !amount || !paymentMethod) return;
  const response = await localFetch('/orders/partial-payment', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify({command_number: command, amount, payment_method: paymentMethod})
  });
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Pagamento parcial', response.ok ? renderSummary(data.payload) : `<pre>${escapeHtml(data.message)}</pre>`);
}

async function openDiscountFlow() {
  const command = activeCommand();
  const type = prompt('Tipo: fixed ou percent', 'fixed');
  const value = prompt('Valor do desconto');
  const reason = prompt('Motivo do desconto');
  if (!command || !type || !value || !reason) return;
  const response = await localFetch('/orders/discount', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify({command_number: command, discount_type: type, value, reason})
  });
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Desconto', response.ok ? renderSummary(data.payload) : `<pre>${escapeHtml(data.message)}</pre>`);
}

async function openMessages() {
  const response = await localFetch('/orders/messages', {headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {messages: []};
  const rows = data.messages.map(msg => `<div class="surface"><strong>${escapeHtml(msg.title)}</strong><div class="muted">${escapeHtml(msg.body)}</div></div>`).join('');
  openModal('Mensagens', rows || '<div class="muted">Nenhuma mensagem.</div>');
}

async function openOutbox() {
  const response = await localFetch('/orders/outbox', {headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {events: []};
  const rows = data.events.map(event => `<div class="surface"><strong>${escapeHtml(event.event_type)}</strong><div class="muted">${escapeHtml(event.sync_status)} | ${escapeHtml(event.created_at)}</div></div>`).join('');
  openModal('Caixa de saida', rows || '<div class="muted">Nenhum evento pendente.</div>');
}

async function startVoiceCommand() {
  const response = await localFetch('/orders/voice-command', {method: 'POST', headers: localHeaders(false)});
  const data = response.ok ? await response.json() : {message: await response.text()};
  openModal('Controle por voz', `<pre>${escapeHtml(data.message)}</pre>`);
}

function openOtherMenu() {
  openModal('Outros', `
    <button class="secondary" type="button" onclick="closeModal(); document.getElementById('product-search').value=''; showScreen('products')">Consultar produto</button>
    <button class="secondary" type="button" onclick="closeModal(); openPrint()">Reimprimir pedido</button>
    <button class="secondary" type="button" onclick="closeModal(); openConsult()">Consultar ${tableLabel().toLowerCase()}</button>
    <button class="secondary" type="button" onclick="openModal('Abrir gaveta', '<pre>Integracao com gaveta ainda nao configurada neste pacote local.</pre>')">Abrir gaveta</button>
  `);
}

function goInitialMenu() {
  if (state.cart.length && !confirm('Existe pedido nao enviado. Deseja sair mesmo assim?')) return;
  showScreen('initial');
}

function printPrebill() {
  const uuid = document.getElementById('print-order').value;
  if (!uuid) {
    document.getElementById('system-message').textContent = 'Nenhuma comanda selecionada.';
    return;
  }
  window.open(`/orders/${uuid}/prebill`, '_blank');
}

loadAppInfo();
loadUsers();
</script>
</body>
</html>
"""
