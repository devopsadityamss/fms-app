// frontend/src/components/farmer/KPIBlock.jsx
import React from "react";

export default function KPIBlock({ title, value }) {
  return (
    <div className="bg-white rounded-xl shadow p-5 flex flex-col items-start">
      <span className="text-sm text-gray-500">{title}</span>
      <span className="text-3xl font-bold text-gray-800 mt-1">
        {value}
      </span>
    </div>
  );
}
