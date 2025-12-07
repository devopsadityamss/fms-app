import React from "react";
import WorkerSidebar from "./WorkerSidebar";
import WorkerHeader from "./WorkerHeader";

export default function WorkerLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <WorkerSidebar />
      <div className="flex-1 flex flex-col">
        <WorkerHeader />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
