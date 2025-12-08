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


// Example role-scoped pages (you can expand these later)
import AdminProjects from "./pages/admin/AdminProjects";
import AdminUsers from "./pages/admin/AdminUsers";

import FarmerTasks from "./pages/farmer/FarmerTasks";
import WorkerTasks from "./pages/worker/WorkerTasks";
import TraderMarket from "./pages/trader/TraderMarket";


// FARMER PRODUCTION UNIT FLOW
import CreateProductionUnit from "./pages/farmer/ProductionUnits/CreateProductionUnit";
import SelectPracticeCategory from "./pages/farmer/ProductionUnits/SelectPracticeCategory";
import SelectPracticeOptions from "./pages/farmer/ProductionUnits/SelectPracticeOptions";
import UnitDetailsForm from "./pages/farmer/ProductionUnits/UnitDetailsForm";
import StageTemplateEditor from "./pages/farmer/ProductionUnits/StageTemplateEditor";
import ProductionUnitView from "./pages/farmer/ProductionUnits/ProductionUnitView";

import FarmerDashboard from "./pages/farmer/FarmerDashboard";


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
      {/* FARMER: Production Unit Creation Flow */}
      <Route
        path="/farmer/production/create"
        element={
          <ProtectedRoute>
            <MainLayout>
              <CreateProductionUnit />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/select-category/:practiceId"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SelectPracticeCategory />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/select-options/:practiceId/:categoryId"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SelectPracticeOptions />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/unit-details/:practiceId/:categoryId"
        element={
          <ProtectedRoute>
            <MainLayout>
              <UnitDetailsForm />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/stages"
        element={
          <ProtectedRoute>
            <MainLayout>
              <StageTemplateEditor />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/unit/:id"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ProductionUnitView />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Farmer Dashboard (optional but recommended) */}
      <Route
        path="/farmer/dashboard"
        element={
          <ProtectedRoute>
            <MainLayout>
              <FarmerDashboard />
            </MainLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
