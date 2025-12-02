// frontend/src/services/api.js

const BASE_URL = "http://localhost:8000";

function buildUrl(path) {
  if (path.startsWith("/")) return BASE_URL + path;
  return BASE_URL + "/" + path;
}

export const api = {
  async get(path, token) {
    return fetch(buildUrl(path), {
      method: "GET",
      headers: {
        "Authorization": token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async post(path, body, token) {
    return fetch(buildUrl(path), {
      method: "POST",
      headers: {
        "Authorization": token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async put(path, body, token) {
    return fetch(buildUrl(path), {
      method: "PUT",
      headers: {
        "Authorization": token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },

  async delete(path, token) {
    return fetch(buildUrl(path), {
      method: "DELETE",
      headers: {
        "Authorization": token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
    }).then((res) => res.json().then((data) => ({ status: res.status, data })));
  },
};
