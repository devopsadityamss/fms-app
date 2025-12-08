// src/App.jsx
import React from "react";
import { Routes, Route } from "react-router-dom";

// Public
import Login from "./pages/Login";
import Register from "./pages/Register";
import RoleRegistration from "./pages/RoleRegistration";

// Protected + Role Router
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardRouter from "./pages/DashboardRouter";

// Layouts
import AdminLayout from "./layout/admin/AdminLayout";
import FarmerLayout from "./layout/farmer/FarmerLayout";
import WorkerLayout from "./layout/worker/WorkerLayout";
import TraderLayout from "./layout/trader/TraderLayout";

// Dashboards (YOU MUST CREATE THESE IF THEY DO NOT EXIST YET)
import AdminDashboard from "./pages/admin/AdminDashboard";
import FarmerDashboard from "./pages/farmer/FarmerDashboard";
import WorkerDashboard from "./pages/worker/WorkerDashboard";
import TraderDashboard from "./pages/trader/TraderDashboard";

// Farmer Pages
import FarmerTasks from "./pages/farmer/FarmerTasks";

// FARMER PRODUCTION UNIT FLOW
import CreateProductionUnit from "./pages/farmer/ProductionUnits/CreateProductionUnit";
import SelectPracticeCategory from "./pages/farmer/ProductionUnits/SelectPracticeCategory";
import SelectPracticeOptions from "./pages/farmer/ProductionUnits/SelectPracticeOptions";
import UnitDetailsForm from "./pages/farmer/ProductionUnits/UnitDetailsForm";
import StageTemplateEditor from "./pages/farmer/ProductionUnits/StageTemplateEditor";
import ProductionUnitView from "./pages/farmer/ProductionUnits/ProductionUnitView";

// Worker Pages
import WorkerTasks from "./pages/worker/WorkerTasks";

// Trader Pages
import TraderMarket from "./pages/trader/TraderMarket";

export default function App() {
  return (
    <Routes>

      {/* ---------- PUBLIC ROUTES ---------- */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/register-roles" element={<RoleRegistration />} />

      {/* ---------- ROOT → AUTO REDIRECT BY ROLE ---------- */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardRouter />
          </ProtectedRoute>
        }
      />

      {/* ---------- ADMIN WORLD ---------- */}
      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminDashboard />
            </AdminLayout>
          </ProtectedRoute>
        }
      />

      {/* You can add more admin pages here using AdminLayout */}

      {/* ---------- FARMER WORLD ---------- */}
      <Route
        path="/farmer/dashboard"
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

      {/* -------- FARMER: PRODUCTION UNIT FLOWS -------- */}
      <Route
        path="/farmer/production/create"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <CreateProductionUnit />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/select-category/:practiceId"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <SelectPracticeCategory />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/select-options/:practiceId/:categoryId"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <SelectPracticeOptions />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/unit-details/:practiceId/:categoryId"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <UnitDetailsForm />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/stages"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <StageTemplateEditor />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer/production/unit/:id"
        element={
          <ProtectedRoute>
            <FarmerLayout>
              <ProductionUnitView />
            </FarmerLayout>
          </ProtectedRoute>
        }
      />

      {/* ---------- WORKER WORLD ---------- */}
      <Route
        path="/worker/dashboard"
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

      {/* ---------- TRADER WORLD ---------- */}
      <Route
        path="/trader/dashboard"
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
