import axios from "axios";

const BASE_URL = "http://localhost:8000";

export const api = {
  get: (url, token) =>
    axios.get(BASE_URL + url, {
      headers: { Authorization: `Bearer ${token}` }
    }),

  post: (url, data, token) =>
    axios.post(BASE_URL + url, data, {
      headers: { Authorization: `Bearer ${token}` }
    }),

  put: (url, data, token) =>
    axios.put(BASE_URL + url, data, {
      headers: { Authorization: `Bearer ${token}` }
    }),

  delete: (url, token) =>
    axios.delete(BASE_URL + url, {
      headers: { Authorization: `Bearer ${token}` }
    })
};
