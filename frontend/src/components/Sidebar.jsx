import React from "react";
import { Link, useLocation } from "react-router-dom";
import { FiHome, FiFolder, FiClipboard, FiLogOut } from "react-icons/fi";
import { supabase } from "../lib/supabase";

const nav = [
  { name: "Dashboard", to: "/", icon: <FiHome /> },
  { name: "Projects", to: "/projects", icon: <FiFolder /> },
  { name: "Tasks", to: "/tasks", icon: <FiClipboard /> },
];

export default function Sidebar() {
  const loc = useLocation();

  const logout = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  return (
    <div className="w-60 bg-white border-r h-screen fixed left-0 top-0 flex flex-col p-5 shadow-sm">
      <h1 className="text-xl font-bold mb-8 tracking-tight">FMS</h1>

      <div className="flex-1 space-y-1">
        {nav.map((item) => (
          <Link
            key={item.name}
            to={item.to}
            className={`flex items-center gap-3 p-3 rounded-lg transition
              ${
                loc.pathname === item.to
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
          >
            {item.icon}
            <span className="text-sm">{item.name}</span>
          </Link>
        ))}
      </div>

      <button
        onClick={logout}
        className="flex items-center gap-3 p-3 text-red-600 hover:bg-red-50 rounded-lg transition text-sm"
      >
        <FiLogOut />
        Logout
      </button>
    </div>
  );
}
