// frontend/src/components/farmer/charts/CostDistributionPie.jsx

import React from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

export default function CostDistributionPie() {
  // Placeholder cost breakdown (₹ values)
  const data = {
    labels: [
      "Seeds",
      "Fertilizers",
      "Pesticides",
      "Labor",
      "Machinery",
      "Irrigation",
      "Feed",
    ],
    datasets: [
      {
        label: "Cost (₹)",
        data: [1200, 2500, 800, 3000, 1500, 900, 2000], // Static placeholder
        backgroundColor: [
          "#3b82f6", // Blue
          "#10b981", // Green
          "#ef4444", // Red
          "#f59e0b", // Yellow
          "#6366f1", // Indigo
          "#0ea5e9", // Cyan
          "#a855f7", // Purple
        ],
        borderColor: "#ffffff",
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className="w-full h-64">
      <Pie data={data} />
    </div>
  );
}
