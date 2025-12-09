// frontend/src/api/farmer.js
import { api } from "./client";

/* ============================================================
   FARMER API WRAPPER (Improved)
   ------------------------------------------------------------
   - Consistent error handling
   - Predictable return structures
   - Non-breaking: all original endpoints preserved
   - Added future-safe task/operation helpers
============================================================ */

function safeReturn(defaultValue) {
  return { ok: false, data: defaultValue };
}

export const farmerApi = {

  /* ---------------------------------------------------------
     DASHBOARD SUMMARY
  --------------------------------------------------------- */
  async getDashboardSummary(userId) {
    if (!userId) return safeReturn(null);
    try {
      const res = await api.get(`/farmer/production-unit/summary/${userId}`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Dashboard summary error:", err);
      return safeReturn(null);
    }
  },

  /* ---------------------------------------------------------
     LIST PRODUCTION UNITS
  --------------------------------------------------------- */
  async listProductionUnits(userId) {
    if (!userId) return safeReturn([]);
    try {
      const res = await api.get(`/farmer/production-unit/list/${userId}`);
      return { ok: true, data: res.data?.units || [] };
    } catch (err) {
      console.error("List units error:", err);
      return safeReturn([]);
    }
  },

  /* ---------------------------------------------------------
     CREATE PRODUCTION UNIT
  --------------------------------------------------------- */
  async createProductionUnit(payload) {
    try {
      const res = await api.post("/farmer/production-unit/create", payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Create unit error:", err);
      throw err;            // UI handles toast
    }
  },

  /* ---------------------------------------------------------
     GET PRODUCTION UNIT DETAILS
  --------------------------------------------------------- */
  async getProductionUnit(unitId) {
    try {
      const res = await api.get(`/farmer/production-unit/${unitId}`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Get unit error:", err);
      return safeReturn(null);
    }
  },

  /* ---------------------------------------------------------
     UPDATE PRODUCTION UNIT
  --------------------------------------------------------- */
  async updateProductionUnit(unitId, payload) {
    try {
      const res = await api.put(`/farmer/production-unit/${unitId}`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Update unit error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     TASKS — CREATE
  --------------------------------------------------------- */
  async addTaskToStage(stageId, payload) {
    try {
      const res = await api.post(`/farmer/production-unit/task/${stageId}`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Create task error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     TASKS — MARK COMPLETE
     (our UI already uses this)
  --------------------------------------------------------- */
  async completeTask(taskId) {
    try {
      const res = await api.post(`/tasks/${taskId}/complete`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Complete task error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     TASKS — GET (NEW)
  --------------------------------------------------------- */
  async getTask(taskId) {
    try {
      const res = await api.get(`/tasks/${taskId}`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Get task error:", err);
      return safeReturn(null);
    }
  },

  /* ---------------------------------------------------------
     TASKS — UPDATE (NEW)
  --------------------------------------------------------- */
  async updateTask(taskId, payload) {
    try {
      const res = await api.patch(`/tasks/${taskId}`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Update task error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     TASKS — DELETE (NEW)
  --------------------------------------------------------- */
  async deleteTask(taskId) {
    try {
      const res = await api.delete(`/tasks/${taskId}`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Delete task error:", err);
      throw err;
    }
  },

  /* ============================================================
     ACTIVITY LOGGING
  ============================================================ */

  async createOperationLog(payload) {
    try {
      const res = await api.post(`/activity/log`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Create op log error:", err);
      throw err;
    }
  },

  async updateOperationLog(logId, payload) {
    try {
      const res = await api.patch(`/activity/log/${logId}`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Update op log error:", err);
      throw err;
    }
  },

  async getOperationLog(logId) {
    try {
      const res = await api.get(`/activity/log/${logId}`);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Fetch log error:", err);
      return safeReturn(null);
    }
  },

  async getUnitOperationLogs(unitId, params = { skip: 0, limit: 50 }) {
    try {
      const res = await api.get(`/activity/${unitId}/logs`, { params });
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("List logs error:", err);
      return safeReturn({ items: [], total: 0 });
    }
  },

  /* ---------------------------------------------------------
     MATERIAL USAGE
  --------------------------------------------------------- */
  async addMaterialUsage(payload) {
    try {
      const res = await api.post(`/activity/material`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Material usage error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     LABOUR USAGE
  --------------------------------------------------------- */
  async addLabourUsage(payload) {
    try {
      const res = await api.post(`/activity/labour`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Labour usage error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     EXPENSE LOGGING
  --------------------------------------------------------- */
  async addExpense(payload) {
    try {
      const res = await api.post(`/activity/expense`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Expense error:", err);
      throw err;
    }
  },

  /* ---------------------------------------------------------
     MEDIA UPLOAD METADATA
  --------------------------------------------------------- */
  async addOperationMedia(payload) {
    try {
      const res = await api.post(`/activity/media`, payload);
      return { ok: true, data: res.data };
    } catch (err) {
      console.error("Media log error:", err);
      throw err;
    }
  },
};
