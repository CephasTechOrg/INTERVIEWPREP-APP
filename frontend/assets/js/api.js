// Central API client (fetch wrapper).
// Change backend URL here if needed.
// Responsibility: provide a single place to attach auth headers and parse responses safely.
const API_BASE = "http://127.0.0.1:8000/api/v1";

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearToken() {
  localStorage.removeItem("token");
}

async function apiFetch(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }

  if (!res.ok) {
    const msg = data?.detail || data?.message || `Request failed (${res.status})`;
    if (auth && (res.status === 401 || res.status === 403)) {
      const lower = String(msg || "").toLowerCase();
      clearToken();
      if (lower.includes("verify")) {
        window.location.href = "./login.html#verify";
      } else {
        window.location.href = "./login.html";
      }
    }
    throw new Error(msg);
  }
  return data;
}

function requireAuthOrRedirect() {
  if (!getToken()) window.location.href = "./login.html";
}

function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }
