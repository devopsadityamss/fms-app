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

// Intelligence Layer APIs

// --- Weather ---
export const getWeatherOverview = (unitId) =>
  api.get(`/farmer/unit/weather/${unitId}`);

export const getWeatherCurrent = (unitId) =>
  api.get(`/farmer/unit/weather/${unitId}/current`);

export const getWeatherHourly = (unitId) =>
  api.get(`/farmer/unit/weather/${unitId}/hourly`);

export const getWeatherDaily = (unitId) =>
  api.get(`/farmer/unit/weather/${unitId}/daily`);

export const getWeatherRisk = (unitId) =>
  api.get(`/farmer/unit/weather/${unitId}/risk`);


// --- Advisory ---
export const getAdvisoryOverview = (unitId, stage) =>
  api.get(`/farmer/unit/advisory/${unitId}`, { params: { stage } });

export const getGeneralAdvisory = (unitId) =>
  api.get(`/farmer/unit/advisory/${unitId}/general`);

export const getStageAdvisory = (unitId, stage) =>
  api.get(`/farmer/unit/advisory/${unitId}/stage`, {
    params: { stage },
  });

export const getWeatherAdvisory = (unitId) =>
  api.get(`/farmer/unit/advisory/${unitId}/weather`);


// --- Alerts ---
export const getAlertsOverview = (unitId, stage, overdue = 0) =>
  api.get(`/farmer/unit/alerts/${unitId}`, {
    params: { stage, overdue_tasks: overdue },
  });

export const getWeatherAlerts = (unitId) =>
  api.get(`/farmer/unit/alerts/${unitId}/weather`);

export const getPestDiseaseAlerts = (unitId, stage) =>
  api.get(`/farmer/unit/alerts/${unitId}/pest-disease`, {
    params: { stage },
  });

export const getTaskAlerts = (unitId, overdue = 0) =>
  api.get(`/farmer/unit/alerts/${unitId}/tasks`, {
    params: { overdue_tasks: overdue },
  });

export const getGrowthAlerts = (unitId) =>
  api.get(`/farmer/unit/alerts/${unitId}/growth`);


// --- Calendar ---
export const getCalendarOverview = (unitId) =>
  api.get(`/farmer/unit/calendar/${unitId}`);

export const getCalendarTimeline = (unitId) =>
  api.get(`/farmer/unit/calendar/${unitId}/timeline`);

export const getCalendarTasks = (unitId) =>
  api.get(`/farmer/unit/calendar/${unitId}/tasks`);

export const getWeeklyOverview = (unitId) =>
  api.get(`/farmer/unit/calendar/${unitId}/weekly`);


// --- Health ---
export const getHealthOverview = (unitId, stage, overdue = 0) =>
  api.get(`/farmer/unit/health/${unitId}`, {
    params: { stage, overdue_tasks: overdue },
  });

export const getHealthScore = (unitId, stage) =>
  api.get(`/farmer/unit/health/${unitId}/score`, {
    params: { stage },
  });


// --- Predictions ---
export const getPredictionsOverview = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}`, { params: { stage } });

export const getYieldPrediction = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}/yield`, { params: { stage } });

export const getHarvestPrediction = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}/harvest`, {
    params: { stage },
  });

export const getWaterPrediction = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}/water`, {
    params: { stage },
  });

export const getFertilizerPrediction = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}/fertilizer`, {
    params: { stage },
  });

export const getCostPrediction = (unitId, stage) =>
  api.get(`/farmer/unit/predictions/${unitId}/cost`, { params: { stage } });


// --- Inventory ---
export const getInventoryOverview = (unitId, stage) =>
  api.get(`/farmer/unit/inventory/${unitId}`, { params: { stage } });

export const getInventoryRequirements = (unitId, stage) =>
  api.get(`/farmer/unit/inventory/${unitId}/requirements`, {
    params: { stage },
  });

export const getInventoryShortages = (unitId, stage) =>
  api.get(`/farmer/unit/inventory/${unitId}/shortages`, {
    params: { stage },
  });

export const getInventoryReorderList = (unitId, stage) =>
  api.get(`/farmer/unit/inventory/${unitId}/reorder`, {
    params: { stage },
  });

export const getInventoryWeeklyForecast = (unitId, stage) =>
  api.get(`/farmer/unit/inventory/${unitId}/weekly`, {
    params: { stage },
  });


// --- Cost ---
export const getCostOverview = (unitId, stage, actualCost = 0) =>
  api.get(`/farmer/unit/cost/${unitId}`, {
    params: { stage, actual_cost: actualCost },
  });

export const getStageCost = (unitId, stage) =>
  api.get(`/farmer/unit/cost/${unitId}/stage`, {
    params: { stage },
  });

export const getCostProjection = (unitId, stage) =>
  api.get(`/farmer/unit/cost/${unitId}/projection`, {
    params: { stage },
  });

export const getCostOverrun = (unitId, stage, actualCost) =>
  api.get(`/farmer/unit/cost/${unitId}/overrun`, {
    params: { stage, actual_cost: actualCost },
  });


// --- Notifications ---
export const getNotificationsOverview = (
  unitId,
  stage,
  overdue = 0,
  upcoming = 0
) =>
  api.get(`/farmer/unit/notifications/${unitId}`, {
    params: {
      stage,
      overdue_tasks: overdue,
      upcoming_tasks: upcoming,
    },
  });

export const getWeatherNotifications = (unitId) =>
  api.get(`/farmer/unit/notifications/${unitId}/weather`);

export const getTaskNotifications = (unitId, overdue = 0, upcoming = 0) =>
  api.get(`/farmer/unit/notifications/${unitId}/tasks`, {
    params: { overdue_tasks: overdue, upcoming_tasks: upcoming },
  });

export const getHealthNotifications = (unitId, stage) =>
  api.get(`/farmer/unit/notifications/${unitId}/health`, {
    params: { stage },
  });

export const getPestNotifications = (unitId, stage) =>
  api.get(`/farmer/unit/notifications/${unitId}/pest`, {
    params: { stage },
  });

export const getStageNotifications = (unitId, stage) =>
  api.get(`/farmer/unit/notifications/${unitId}/stage`, {
    params: { stage },
  });
