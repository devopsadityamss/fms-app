import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function WorkerSidebar() {
  const loc = useLocation();
  const items = [
    { name: "Dashboard", to: "/worker" },
    { name: "My Tasks", to: "/worker/tasks" },
    { name: "Work Log", to: "/worker/work-log" },
  ];

  return (
    <aside className="w-56 bg-white border-r h-screen fixed left-0 top-0 p-5">
      <div className="text-lg font-bold mb-6">Worker</div>
      <nav className="space-y-2">
        {items.map((it) => (
          <Link
            key={it.to}
            to={it.to}
            className={`block p-3 rounded-lg ${loc.pathname === it.to ? "bg-orange-500 text-white" : "text-slate-700 hover:bg-slate-100"}`}
          >
            {it.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
