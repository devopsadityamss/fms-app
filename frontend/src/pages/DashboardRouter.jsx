// src/pages/DashboardRouter.jsx
import React from "react";
import { useUser } from "../context/UserContext";
import { Navigate } from "react-router-dom";

export default function DashboardRouter() {
  const { activeRole } = useUser();

  if (!activeRole) {
    // still loading or no role set
    return <div className="p-6">Loading dashboard...</div>;
  }

  switch ((activeRole || "").toLowerCase()) {
    case "admin":
      return <Navigate to="/admin" replace />;

    case "farmer":
      return <Navigate to="/farmer" replace />;

    case "worker":
      return <Navigate to="/worker" replace />;

    case "trader":
      return <Navigate to="/trader" replace />;

    default:
      return <div className="p-6">Unknown role: {activeRole}</div>;
  }
}
