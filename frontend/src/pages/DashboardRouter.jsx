// src/pages/DashboardRouter.jsx
import React from "react";
import { useUser } from "../context/UserContext";
import { Navigate } from "react-router-dom";

export default function DashboardRouter() {
  const { activeRole } = useUser();

  if (!activeRole) {
    return <div className="p-6">Loading dashboard...</div>;
  }

  const role = activeRole.toLowerCase();

  switch (role) {
    case "admin":
      return <Navigate to="/admin/dashboard" replace />;

    case "farmer":
      return <Navigate to="/farmer/dashboard" replace />;

    case "worker":
      return <Navigate to="/worker/dashboard" replace />;

    case "trader":
      return <Navigate to="/trader/dashboard" replace />;

    default:
      return <div className="p-6">Unknown role: {activeRole}</div>;
  }
}
