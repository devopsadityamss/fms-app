// frontend/src/services/api.js

// ------------------------------
// BASE URL
// ------------------------------
const BASE_URL = "http://127.0.0.1:8000";

function buildUrl(path) {
  if (path.startsWith("/")) return BASE_URL + path;
  return BASE_URL + "/" + path;
}

// ------------------------------
// NEW: Backend token management
// ------------------------------
let backendToken = localStorage.getItem("fms_backend_token") || null;

export function setBackendToken(token) {
  backendToken = token;
  if (token) {
    localStorage.setItem("fms_backend_token", token);
  } else {
    localStorage.removeItem("fms_backend_token");
  }
}

// ✅ ADDED — getter for ProtectedRoute & other components
export function getBackendToken() {
  return backendToken;
}

function authHeader(explicitToken) {
  const token = explicitToken || backendToken;
  return token ? `Bearer ${token}` : "";
}

// ------------------------------
// EXISTING API METHODS (unchanged except token handling)
// ------------------------------
export const api = {
  async get(path, token) {
    return fetch(buildUrl(path), {
      method: "GET",
      headers: {
        "Authorization": authHeader(token),
        "Content-Type": "application/json",
      },
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async post(path, body, token) {
    return fetch(buildUrl(path), {
      method: "POST",
      headers: {
        "Authorization": authHeader(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async put(path, body, token) {
    return fetch(buildUrl(path), {
      method: "PUT",
      headers: {
        "Authorization": authHeader(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async delete(path, token) {
    return fetch(buildUrl(path), {
      method: "DELETE",
      headers: {
        "Authorization": authHeader(token),
        "Content-Type": "application/json",
      },
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },
};
