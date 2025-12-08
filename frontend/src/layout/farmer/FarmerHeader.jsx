import React, { useState } from "react";
import { useUser } from "../../context/UserContext";

export default function FarmerHeader() {
  const { supabaseUser, roles, activeRole, switchRole, logout } = useUser();
  const [open, setOpen] = useState(false);

  return (
    <header className="h-16 bg-white border-b flex items-center justify-between px-6 shadow-sm">
      
      {/* LEFT SIDE */}
      <div className="text-lg font-semibold text-emerald-700">
        Farmer Portal
      </div>

      {/* RIGHT SIDE */}
      <div className="relative flex items-center gap-4">

        {/* USER BADGE */}
        <div
          className="px-3 py-1 rounded-full text-sm bg-emerald-50 text-emerald-700 cursor-pointer"
          onClick={() => setOpen(!open)}
        >
          {activeRole?.toUpperCase() || "ROLE"}
        </div>

        {/* ROLE SWITCH DROPDOWN */}
        {open && (
          <div className="absolute right-0 top-12 bg-white shadow-lg rounded-lg border w-48 py-2 z-50">
            <div className="px-4 py-1 text-xs text-gray-500">Switch Role</div>

            {roles?.map((role) => (
              <button
                key={role}
                onClick={() => {
                  switchRole(role);
                  setOpen(false);
                }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${
                  activeRole === role ? "font-semibold text-emerald-700" : ""
                }`}
              >
                {role.toUpperCase()}
              </button>
            ))}

            <hr className="my-2" />

            {/* Logout */}
            <button
              onClick={() => logout()}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              Logout
            </button>
          </div>
        )}

        {/* User avatar */}
        <div className="w-8 h-8 flex items-center justify-center rounded-full bg-emerald-100 text-emerald-700 font-bold">
          {supabaseUser?.email?.[0]?.toUpperCase() || "U"}
        </div>
      </div>
    </header>
  );
}
