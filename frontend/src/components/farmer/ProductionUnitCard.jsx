// frontend/src/components/farmer/ProductionUnitCard.jsx

import React from "react";

export default function ProductionUnitCard({ unit }) {
  return (
    <div className="bg-white rounded-xl shadow p-6 flex flex-col space-y-4">

      {/* Unit Name */}
      <h3 className="text-lg font-semibold text-gray-800">
        {unit.name}
      </h3>

      {/* Practice Type */}
      <div className="text-sm text-gray-500">
        {unit.practice_type?.toUpperCase() || "UNKNOWN TYPE"}
      </div>

      {/* Progress Bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Progress</span>
          <span>{unit.progress || 0}%</span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-2 bg-emerald-500"
            style={{ width: `${unit.progress || 0}%` }}
          ></div>
        </div>
      </div>

      {/* Next Task */}
      <div className="text-sm text-gray-700">
        <span className="font-semibold">Next Task:</span>{" "}
        {unit.next_task || "No upcoming tasks"}
      </div>

      {/* Status Badge */}
      <div className="mt-2">
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            unit.health_status === "good"
              ? "bg-emerald-100 text-emerald-700"
              : unit.health_status === "warning"
              ? "bg-yellow-100 text-yellow-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {unit.health_status
            ? unit.health_status.toUpperCase()
            : "UNKNOWN"}
        </span>
      </div>

      {/* Open Button */}
      <button
        onClick={() => (window.location.href = `/farmer/units/${unit.id}`)}
        className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-700"
      >
        Open Unit
      </button>
    </div>
  );
}
