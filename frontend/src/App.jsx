import React from "react";
import { Routes, Route, BrowserRouter } from "react-router-dom";   // ← Updated: added BrowserRouter

import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import TaskBoard from "./pages/TaskBoard";
import TaskDetail from "./pages/TaskDetail";
import ProjectDetail from "./pages/ProjectDetail";   // ← ADDED
import Login from "./pages/Login";                    // ← ADDED
import Register from "./pages/Register";              // ← ADDED
import ProtectedRoute from "./components/ProtectedRoute";   // ← ADDED
import { UserProvider } from "./context/UserContext";       // ← ADDED

export default function App() {
  return (
    <UserProvider>                                      // ← ADDED
      <BrowserRouter>                                   // ← ADDED
        <Routes>

          {/* Auth */}
          <Route path="/login" element={<Login />} />           // ← ADDED
          <Route path="/register" element={<Register />} />     // ← ADDED

          {/* Protected pages */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />                                                    // ← Updated

          <Route
            path="/projects"
            element={
              <ProtectedRoute>
                <Projects />
              </ProtectedRoute>
            }
          />                                                    // ← Updated

          <Route path="/projects/:id" element={<ProjectDetail />} />   // ← ADDED

          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <TaskBoard />
              </ProtectedRoute>
            }
          />                                                    // ← Updated

          <Route
            path="/tasks/:id"
            element={
              <ProtectedRoute>
                <TaskDetail />
              </ProtectedRoute>
            }
          />                                                    // ← Updated

          <Route path="/profile" element={<div>Profile Page</div>} />

        </Routes>
      </BrowserRouter>                                   // ← ADDED
    </UserProvider>                                      // ← ADDED
  );
}