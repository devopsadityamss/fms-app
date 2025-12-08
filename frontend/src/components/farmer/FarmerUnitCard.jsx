// frontend/components/farmer/FarmerUnitCard.jsx
import React from "react";

export default function FarmerUnitCard({ unit, onOpen }) {
  const progress = unit?.progress ?? 0;
  const health = unit?.health_status ?? "unknown";

  const healthColor =
    health === "excellent" ? "bg-green-100 text-green-800" :
    health === "good" ? "bg-amber-100 text-amber-800" :
    health === "warning" ? "bg-red-100 text-red-800" :
    "bg-slate-100 text-slate-700";

  return (
    <div className="bg-white rounded shadow p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-lg">{unit.name}</h3>
          <span className={`text-xs font-semibold px-2 py-1 rounded ${healthColor}`}>
            {health?.toUpperCase?.() || "N/A"}
          </span>
        </div>

        <div className="text-sm text-gray-500 mt-1">{unit.practice_type}</div>

        <div className="mt-4">
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 rounded-full"
              style={{
                width: `${progress}%`,
                background: progress >= 70 ? "#10b981" : progress >= 30 ? "#f59e0b" : "#ef4444",
                transition: "width 0.3s",
              }}
            />
          </div>
          <div className="text-xs text-gray-500 mt-2">Progress: {progress}%</div>
        </div>

        {unit.next_task && (
          <div className="mt-3 text-sm text-gray-700">
            <strong>Next:</strong> {unit.next_task}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <button
          onClick={() => onOpen?.(unit)}
          className="px-3 py-1 bg-indigo-600 text-white rounded text-sm"
        >
          Open
        </button>

        <div className="text-xs text-gray-400">ID: {String(unit.id).slice(0, 8)}</div>
      </div>
    </div>
  );
}
