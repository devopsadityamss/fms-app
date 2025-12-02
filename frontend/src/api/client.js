import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Helper functions (optional, but useful)
export const fetchProjects = () => api.get("/projects").then((res) => res.data);
export const fetchTasks = (project_id) =>
  api
    .get("/tasks", { params: project_id ? { project_id } : {} })
    .then((res) => res.data);

export const fetchTask = (id) =>
  api.get(`/tasks/${id}`).then((res) => res.data);

export const createTask = (data) =>
  api.post("/tasks", data).then((res) => res.data);

export const updateTask = (id, data) =>
  api.put(`/tasks/${id}`, data).then((res) => res.data);
