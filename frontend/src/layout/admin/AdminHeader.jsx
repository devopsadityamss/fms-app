// src/layout/admin/AdminHeader.jsx
import React from "react";
import { useUser } from "../../context/UserContext";

export default function AdminHeader() {
  const { activeRole, logout } = useUser();
  return (
    <header className="h-16 bg-white border-b flex items-center justify-between px-6">
      <div className="text-lg font-semibold">Admin Console</div>
      <div className="flex items-center gap-4">
        <div className="px-3 py-1 rounded-full text-sm bg-emerald-50 text-emerald-700">{activeRole?.toUpperCase()}</div>
        <button onClick={() => logout()} className="px-3 py-1 text-sm text-red-600">Logout</button>
      </div>
    </header>
  );
}
