// src/App.jsx
import React from "react";
import { Routes, Route } from "react-router-dom";

// Public
import Login from "./pages/Login";
import Register from "./pages/Register";
import RoleRegistration from "./pages/RoleRegistration";

// Router + Protected
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardRouter from "./pages/DashboardRouter";

// Role layouts
import AdminLayout from "./layout/admin/AdminLayout";
import FarmerLayout from "./layout/farmer/FarmerLayout";
import WorkerLayout from "./layout/worker/WorkerLayout";
import TraderLayout from "./layout/trader/TraderLayout";

// Role dashboards (you said you already created these)
import AdminDashboard from "./pages/dashboards/AdminDashboard";
import FarmerDashboard from "./pages/dashboards/FarmerDashboard";
import WorkerDashboard from "./pages/dashboards/WorkerDashboard";
import TraderDashboard from "./pages/dashboards/TraderDashboard";

// Example role-scoped pages (you can expand these later)
import AdminProjects from "./pages/admin/AdminProjects";
import AdminUsers from "./pages/admin/AdminUsers";

import FarmerTasks from "./pages/farmer/FarmerTasks";
import WorkerTasks from "./pages/worker/WorkerTasks";
import TraderMarket from "./pages/trader/TraderMarket";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/register-roles" element={<RoleRegistration />} />

      {/* Root → redirect to role world */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardRouter />
          </ProtectedRoute>
        }
      />

      {/* ----------------- ADMIN WORLD ----------------- */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminDashboard />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/projects"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminProjects />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminUsers />
            </AdminLayout>
          </ProtectedRoute>
        }
      />

      {/* ----------------- FARMER WORLD ----------------- */}
      <Route
        path="/farmer"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <FarmerDashboard />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/farmer/tasks"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <FarmerTasks />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      {/* ----------------- WORKER WORLD ----------------- */}
      <Route
        path="/worker"
        element={
          <ProtectedRoute>
            <WorkerLayout>
              <WorkerDashboard />
            </WorkerLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/worker/tasks"
        element={
          <ProtectedRoute>
            <WorkerLayout>
              <WorkerTasks />
            </WorkerLayout>
          </ProtectedRoute>
        }
      />

      {/* ----------------- TRADER WORLD ----------------- */}
      <Route
        path="/trader"
        element={
          <ProtectedRoute>
            <TraderLayout>
              <TraderDashboard />
            </TraderLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trader/market"
        element={
          <ProtectedRoute>
            <TraderLayout>
              <TraderMarket />
            </TraderLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
