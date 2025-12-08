// frontend/services/productionApi.js
import { api } from "../services/api"; // matches your project usage
import { getBackendToken } from "./tokenHelper";

/**
 * Helper: get token (prefer context, fallback to localStorage)
 * - Some files in your repo pass token to api.get like api.get("/path", token)
 * - This wrapper will call api.get with token when needed
 */
function tokenForUse(userToken) {
  // prefer explicit userToken, else try localStorage key used elsewhere
  return userToken || getBackendToken();
}

export async function listProductionUnits(userId, userToken = null) {
  const token = tokenForUse(userToken);
  const res = await api.get(`/farmer/production-unit/list/${userId}`, token);
  return res.data?.units || [];
}

export async function getDashboardSummary(userId, userToken = null) {
  const token = tokenForUse(userToken);
  const res = await api.get(`/farmer/production-unit/summary/${userId}`, token);
  return res.data || res;
}
