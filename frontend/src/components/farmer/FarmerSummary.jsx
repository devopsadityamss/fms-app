// frontend/components/farmer/FarmerSummary.jsx
import React from "react";

export default function FarmerSummary({ summary }) {
  // safe defaults
  const {
    total_units = 0,
    active_units = 0,
    upcoming_tasks = 0,
    overdue_tasks = 0,
    total_expenses = 0,
    profit_index = 0,
  } = summary || {};

  const kpi = [
    { label: "Units", value: total_units },
    { label: "Active", value: active_units },
    { label: "Upcoming", value: upcoming_tasks },
    { label: "Overdue", value: overdue_tasks },
    { label: "Expenses", value: typeof total_expenses === "number" ? `₹ ${total_expenses}` : total_expenses },
    { label: "Profit Index", value: profit_index },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
      {kpi.map((k) => (
        <div key={k.label} className="bg-white p-4 rounded shadow flex flex-col">
          <div className="text-xs text-gray-500">{k.label}</div>
          <div className="text-xl font-bold mt-1">{k.value}</div>
        </div>
      ))}
    </div>
  );
}
