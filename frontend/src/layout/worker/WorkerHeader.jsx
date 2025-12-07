import React from "react";
import { useUser } from "../../context/UserContext";

export default function WorkerHeader() {
  const { activeRole, logout } = useUser();
  return (
    <header className="h-14 bg-white border-b flex items-center justify-between px-6">
      <div className="text-lg font-semibold">Worker Portal</div>
      <div className="flex items-center gap-4">
        <div className="px-3 py-1 rounded-full text-sm bg-orange-50 text-orange-600">{activeRole?.toUpperCase()}</div>
        <button onClick={() => logout()} className="px-3 py-1 text-sm text-red-600">Logout</button>
      </div>
    </header>
  );
}
