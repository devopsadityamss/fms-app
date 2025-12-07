import React, { useEffect, useState } from "react";
import { useUser } from "../context/UserContext";
import RoleSelector from "./RoleSelector";

export default function Header() {
  const [isDark, setIsDark] = useState(() => localStorage.getItem("fms_dark") === "1");

  // ⭐ NEW: Role switching state
  const { roles, activeRole, switchRole } = useUser();
  const [showRoleSelector, setShowRoleSelector] = useState(false);

  useEffect(() => {
    if (isDark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
    localStorage.setItem("fms_dark", isDark ? "1" : "0");
  }, [isDark]);

  const handleRoleSelect = async (role) => {
    await switchRole(role);
    setShowRoleSelector(false);
  };

  return (
    <header className="bg-white dark:bg-slate-800 shadow p-4 flex items-center justify-between">
      <h2 className="text-lg font-semibold dark:text-white">FMS App</h2>

      <div className="flex items-center gap-4">
        {/* ⭐ ACTIVE ROLE BADGE */}
        <div
          className="px-4 py-1 rounded-full border font-semibold"
          style={{
            borderColor: "#10b981",
            color: "#059669",
            background: "#10b98120",
          }}
        >
          {activeRole ? activeRole.toUpperCase() : "NO ROLE"}
        </div>

        {/* ⭐ SWITCH ROLE BUTTON */}
        <button
          onClick={() => setShowRoleSelector(true)}
          className="px-3 py-1 rounded bg-slate-900 text-white dark:bg-slate-700"
        >
          Switch Role
        </button>

        {/* Existing Dark Mode Toggle */}
        <button
          onClick={() => setIsDark(!isDark)}
          className="px-2 py-1 rounded border dark:border-slate-700"
        >
          {isDark ? "🌙" : "☀️"}
        </button>

        {/* Existing Placeholder Avatar */}
        <div className="w-8 h-8 rounded-full bg-slate-400"></div>
      </div>

      {/* ⭐ GLOBAL ROLE SELECT MODAL */}
      {showRoleSelector && (
        <RoleSelector
          roles={roles}
          onSelect={handleRoleSelect}
          onCancel={() => setShowRoleSelector(false)}
        />
      )}
    </header>
  );
}
