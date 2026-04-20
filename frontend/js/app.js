import { api } from "./api.js";
import { login, logout, me } from "./auth.js";
import { sectionTitle, summaryCard } from "./components.js";

const app = document.querySelector("#app");

function renderLogin(error = "") {
  app.innerHTML = `
    <div class="container" style="max-width:460px;margin-top:60px;">
      <div class="card">
        <h1 class="title">MoviSys Admin</h1>
        <p class="subtitle">Autenticação JWT comercial</p>
        <form id="login-form">
          <label>Email <input type="email" name="email" required /></label>
          <label>Senha <input type="password" name="password" required /></label>
          ${error ? `<div class="error">${error}</div>` : ""}
          <button class="btn btn-primary" type="submit">Entrar</button>
        </form>
      </div>
    </div>
  `;
  document.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await login(form.get("email"), form.get("password"));
      await renderDashboard();
    } catch (err) {
      renderLogin(err.message);
    }
  });
}

function userTableRows(users) {
  return users
    .map(
      (user) => `
      <tr>
        <td>${user.nome}</td>
        <td>${user.email}</td>
        <td>${user.role}</td>
        <td><span class="pill ${user.ativo ? "pill-ok" : "pill-warn"}">${user.ativo ? "Ativo" : "Inativo"}</span></td>
      </tr>
    `
    )
    .join("");
}

function empresaTableRows(empresas) {
  return empresas
    .map(
      (empresa) => `
      <tr>
        <td>${empresa.nome}</td>
        <td>${empresa.cnpj}</td>
        <td><span class="pill ${empresa.ativo ? "pill-ok" : "pill-warn"}">${empresa.ativo ? "Ativa" : "Inativa"}</span></td>
      </tr>
    `
    )
    .join("");
}

async function renderDashboard() {
  const currentUser = await me();
  const summary = await api.get("/v1/dashboard/summary");
  const empresas = await api.get("/v1/empresas");
  const users = await api.get("/v1/usuarios");

  app.innerHTML = `
    <div class="container">
      <div class="header">
        <div>
          <h1 class="title">Painel Administrativo</h1>
          <p class="subtitle">${currentUser.nome} (${currentUser.role}) - CNPJ ${currentUser.empresa_cnpj}</p>
        </div>
        <button id="logout-btn" class="btn btn-danger">Sair</button>
      </div>

      <div class="grid">
        ${summaryCard("Empresas", summary.empresas)}
        ${summaryCard("Usuarios", summary.usuarios)}
        ${summaryCard("Usuarios ativos", summary.ativos)}
      </div>

      <div style="height:16px"></div>
      <div class="grid">
        <div class="card">
          ${sectionTitle("Gestao de Empresas", "Estrutura multi-tenant por CNPJ")}
          <table>
            <thead><tr><th>Nome</th><th>CNPJ</th><th>Status</th></tr></thead>
            <tbody>${empresaTableRows(empresas)}</tbody>
          </table>
        </div>
        <div class="card">
          ${sectionTitle("Gestao de Usuarios", "Controle de acesso por empresa")}
          <table>
            <thead><tr><th>Nome</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
            <tbody>${userTableRows(users)}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  document.querySelector("#logout-btn").addEventListener("click", async () => {
    await logout();
    renderLogin();
  });
}

async function bootstrap() {
  try {
    await me();
    await renderDashboard();
  } catch {
    renderLogin();
  }
}

bootstrap();
