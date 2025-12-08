// frontend/src/api/farmer.js

import { api } from "./client";

/**
 * Farmer API Wrapper
 * All farmer-related backend calls are defined here.
 */

export const farmerApi = {
  // -------------------------------------------
  // 1) GET DASHBOARD SUMMARY
  // -------------------------------------------
  async getDashboardSummary(userId) {
    try {
      // FIXED: must call /farmer/production-unit/summary/{userId}
      const res = await api.get(`/farmer/production-unit/summary/${userId}`);
      return res.data;
    } catch (err) {
      console.error("Error fetching dashboard summary:", err);
      return null;
    }
  },

  // -------------------------------------------
  // 2) LIST PRODUCTION UNITS
  // -------------------------------------------
  async listProductionUnits(userId) {
    try {
      // FIXED: your original path was correct
      const res = await api.get(`/farmer/production-unit/list/${userId}`);
      return res.data?.units || [];
    } catch (err) {
      console.error("Error fetching production units:", err);
      return [];
    }
  },

  // -------------------------------------------
  // 3) CREATE PRODUCTION UNIT
  // -------------------------------------------
  async createProductionUnit(payload) {
    try {
      // unchanged — path is correct
      const res = await api.post("/farmer/production-unit/create", payload);
      return res.data;
    } catch (err) {
      console.error("Error creating production unit:", err);
      throw err;
    }
  },

  // -------------------------------------------
  // 4) GET UNIT DETAILS (Stages + Tasks)
  // -------------------------------------------
  async getProductionUnit(unitId) {
    try {
      // unchanged — matches backend `/farmer/production-unit/{unit_id}`
      const res = await api.get(`/farmer/production-unit/${unitId}`);
      return res.data;
    } catch (err) {
      console.error("Error fetching unit:", err);
      return null;
    }
  },

  // -------------------------------------------
  // 5) (NEW) UPDATE PRODUCTION UNIT — optional
  // -------------------------------------------
  async updateProductionUnit(unitId, payload) {
    try {
      const res = await api.put(`/farmer/production-unit/${unitId}`, payload);
      return res.data;
    } catch (err) {
      console.error("Error updating unit:", err);
      throw err;
    }
  },

  // -------------------------------------------
  // 6) (NEW) CREATE TASK inside unit — optional
  // -------------------------------------------
  async addTaskToStage(stageId, payload) {
    try {
      const res = await api.post(`/farmer/production-unit/task/${stageId}`, payload);
      return res.data;
    } catch (err) {
      console.error("Error creating task:", err);
      throw err;
    }
  },

  // -------------------------------------------
  // 7) (NEW) Mark Task as Completed — optional
  // -------------------------------------------
  async completeTask(taskId) {
    try {
      const res = await api.post(`/farmer/production-unit/task/${taskId}/complete`);
      return res.data;
    } catch (err) {
      console.error("Error completing task:", err);
      throw err;
    }
  },
};
