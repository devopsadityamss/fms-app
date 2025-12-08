import React from "react";
import FarmerSidebar from "./FarmerSidebar";
import FarmerHeader from "./FarmerHeader";

export default function FarmerLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-emerald-50">
      
      {/* LEFT SIDEBAR */}
      <FarmerSidebar />

      {/* MAIN AREA */}
      <div className="flex-1 flex flex-col overflow-y-auto">

        {/* STICKY HEADER */}
        <div className="sticky top-0 z-20 bg-emerald-50">
          <FarmerHeader />
        </div>

        {/* PAGE CONTENT */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
