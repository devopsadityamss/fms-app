// frontend/services/tokenHelper.js

export function getBackendToken() {
  // prefer the localStorage key that has been used in your repo earlier
  const t = localStorage.getItem("fms_backend_token") || localStorage.getItem("fms_backend_token");
  return t || null;
}
