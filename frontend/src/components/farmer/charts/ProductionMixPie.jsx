// frontend/src/components/farmer/charts/ProductionMixPie.jsx

import React from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

export default function ProductionMixPie() {
  // Placeholder data — backend integration will come later
  const data = {
    labels: ["Crop Farming", "Dairy", "Fisheries", "Plantation", "Poultry"],
    datasets: [
      {
        label: "Units",
        data: [4, 2, 1, 1, 0], // Static placeholder
        backgroundColor: [
          "#10b981",
          "#3b82f6",
          "#6366f1",
          "#f59e0b",
          "#ef4444",
        ],
        borderColor: ["#ffffff"],
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
