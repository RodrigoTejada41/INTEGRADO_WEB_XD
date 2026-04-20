import { api } from "./api.js";

export async function login(email, password) {
  const data = await api.post("/v1/auth/login", { email, password });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
}

export async function logout() {
  const refreshToken = localStorage.getItem("refresh_token");
  if (refreshToken) {
    await api.post("/v1/auth/logout", { refresh_token: refreshToken }).catch(() => null);
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function me() {
  return api.get("/v1/auth/me");
}
