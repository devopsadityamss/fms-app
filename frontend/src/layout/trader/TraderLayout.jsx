import React from "react";
import TraderSidebar from "./TraderSidebar";
import TraderHeader from "./TraderHeader";

export default function TraderLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <TraderSidebar />
      <div className="flex-1 flex flex-col">
        <TraderHeader />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
