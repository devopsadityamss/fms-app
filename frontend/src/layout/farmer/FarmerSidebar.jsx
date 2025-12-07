import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function FarmerSidebar() {
  const loc = useLocation();
  const items = [
    { name: "Dashboard", to: "/farmer" },
    { name: "Tasks", to: "/farmer/tasks" },
    { name: "Crops", to: "/farmer/crops" },
    { name: "Equipment", to: "/farmer/equipment" },
  ];

  return (
    <aside className="w-64 bg-white border-r h-screen fixed left-0 top-0 p-6">
      <div className="text-xl font-bold mb-6 text-emerald-700">Farmer</div>
      <nav className="space-y-2">
        {items.map((it) => (
          <Link
            key={it.to}
            to={it.to}
            className={`block p-3 rounded-lg ${loc.pathname === it.to ? "bg-emerald-600 text-white" : "text-emerald-700 hover:bg-emerald-50"}`}
          >
            {it.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
