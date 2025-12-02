import React from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

export default function MainLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <div className="flex flex-col flex-1">
        <Header />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
