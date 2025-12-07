import React from "react";
import FarmerSidebar from "./FarmerSidebar";
import FarmerHeader from "./FarmerHeader";

export default function FarmerLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-emerald-50">
      <FarmerSidebar />
      <div className="flex-1 flex flex-col">
        <FarmerHeader />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
