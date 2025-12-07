import React from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

export default function MainLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-slate-100">
      {/* FIXED SIDEBAR */}
      <Sidebar />

      {/* RIGHT SIDE CONTENT AREA */}
      <div className="flex flex-col flex-1 ml-60">
        {/* GLOBAL HEADER */}
        <Header />

        {/* MAIN PAGE CONTENT */}
        <main className="p-6 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
