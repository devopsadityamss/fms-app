import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function TraderSidebar() {
  const loc = useLocation();
  const items = [
    { name: "Dashboard", to: "/trader" },
    { name: "Market", to: "/trader/market" },
    { name: "Orders", to: "/trader/orders" },
  ];

  return (
    <aside className="w-64 bg-white border-r h-screen fixed left-0 top-0 p-6">
      <div className="text-xl font-bold mb-6">Trader</div>
      <nav className="space-y-2">
        {items.map((it) => (
          <Link
            key={it.to}
            to={it.to}
            className={`block p-3 rounded-lg ${loc.pathname === it.to ? "bg-sky-600 text-white" : "text-slate-700 hover:bg-slate-100"}`}
          >
            {it.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
