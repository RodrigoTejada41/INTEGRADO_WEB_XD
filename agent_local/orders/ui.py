from __future__ import annotations


def render_orders_ui() -> str:
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comandas Locais</title>
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
    @media (min-width: 700px) {
      .screen { padding: 18px; }
      .actions { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .menu { grid-template-columns: repeat(4, minmax(0, 1fr)); }
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
      <div id="title" class="title">Comandas Locais</div>
      <div id="subtitle" class="subtitle">API local separada do sync de relatorios</div>
    </div>
    <div id="user-badge" class="user-badge">Sem usuario</div>
  </header>

  <main>
    <section id="screen-login" class="screen active">
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

    <section id="screen-menu" class="screen">
      <div class="menu">
        <button type="button" onclick="startOrder()">Pedido</button>
        <button type="button" onclick="openConsult()">Consultar comanda</button>
        <button type="button" onclick="openPrint()">Imprimir pre-conta</button>
        <button type="button" onclick="logout()">Sair</button>
      </div>
    </section>

    <section id="screen-start" class="screen">
      <div class="surface stack">
        <div class="grid two">
          <div>
            <label>Numero da comanda</label>
            <input id="command-number" inputmode="numeric" autocomplete="off">
          </div>
          <div>
            <label>Quantidade de pessoas</label>
            <input id="people-count" type="number" min="1" step="1" inputmode="numeric">
          </div>
          <div>
            <label>Mesa</label>
            <input id="table-reference" autocomplete="off">
          </div>
        </div>
        <div class="actions">
          <button class="primary" type="button" onclick="goProducts()">Selecionar produtos</button>
          <button class="secondary" type="button" onclick="showScreen('menu')">Voltar</button>
        </div>
        <div class="muted">A comanda identifica o pedido. A mesa e apenas referencia fisica.</div>
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
            <label>Mesa</label>
            <input id="consult-table" autocomplete="off">
          </div>
          <div>
            <label>Comanda</label>
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
          <thead><tr><th>Comanda</th><th>Mesa</th><th>Status</th><th>Total</th><th></th></tr></thead>
          <tbody id="orders"></tbody>
        </table>
      </div>
    </section>

    <section id="screen-print" class="screen">
      <div class="surface stack">
        <div>
          <label>Comanda para pre-conta</label>
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

<script>
const state = {
  sessionToken: '',
  operator: null,
  families: [],
  products: [],
  selectedFamily: '',
  cart: [],
  searchTimer: null
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
    login: 'Comandas Locais',
    menu: 'Menu principal',
    start: 'Novo pedido',
    products: 'Selecionar produtos',
    review: 'Revisar pedido',
    consult: 'Consultar comanda',
    print: 'Imprimir pre-conta'
  }[name];
}

function money(value) {
  return Number(value || 0).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

async function loadUsers() {
  const message = document.getElementById('login-message');
  const select = document.getElementById('operator-code');
  message.textContent = 'Carregando usuarios...';
  const response = await fetch('/orders/users', {headers: localHeaders(false)});
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

async function login() {
  const message = document.getElementById('login-message');
  const payload = {
    operator_code: document.getElementById('operator-code').value,
    password: document.getElementById('operator-password').value
  };
  const response = await fetch('/orders/login', {
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
  document.getElementById('user-badge').textContent = data.operator.name;
  message.className = 'success';
  message.textContent = 'Login autorizado.';
  await loadFamilies();
  showScreen('menu');
}

function logout() {
  state.sessionToken = '';
  state.operator = null;
  state.cart = [];
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
  if (!command || !table) {
    alert('Informe comanda e mesa.');
    return;
  }
  await loadProducts();
  showScreen('products');
}

async function loadFamilies() {
  const response = await fetch('/orders/product-families', {headers: localHeaders(false)});
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
  const response = await fetch(`/orders/products?${params.toString()}`, {headers: localHeaders(false)});
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
  document.getElementById('review-header').textContent = `Comanda ${command}`;
  document.getElementById('review-meta').textContent = `Mesa ${table} | Pessoas ${document.getElementById('people-count').value || '-'}`;
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
    table_reference: document.getElementById('table-reference').value.trim(),
    operator_code: state.operator ? state.operator.code : null,
    items: state.cart.map(item => ({
      product_code: item.product_code,
      description: item.description,
      quantity: String(item.quantity),
      unit_price: String(item.unit_price),
      notes: item.notes || null
    }))
  };
  const response = await fetch('/orders/confirm', {
    method: 'POST',
    headers: localHeaders(),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    alert(await response.text());
    return;
  }
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
  const response = await fetch(url, {headers: localHeaders(false)});
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
    <option value="${escapeHtml(order.uuid)}">Comanda ${escapeHtml(order.command_number)} - Mesa ${escapeHtml(order.table_reference || '')}</option>
  `).join('');
}

function printPrebill() {
  const uuid = document.getElementById('print-order').value;
  if (!uuid) {
    document.getElementById('system-message').textContent = 'Nenhuma comanda selecionada.';
    return;
  }
  window.open(`/orders/${uuid}/prebill`, '_blank');
}

loadUsers();
</script>
</body>
</html>
"""
