// frontend/src/components/farmer/charts/ProgressLineChart.jsx

import React from "react";
import {
  Line
} from "react-chartjs-2";

import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend
);

export default function ProgressLineChart() {
  // Placeholder X-axis: farming cycle weeks
  const labels = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6"];

  // Placeholder dataset
  const data = {
    labels,
    datasets: [
      {
        label: "Expected Progress (%)",
        data: [5, 15, 30, 50, 70, 100], // Ideal curve
        borderColor: "#10b981",
        backgroundColor: "#10b98150",
        tension: 0.4,
      },
      {
        label: "Actual Progress (%)",
        data: [4, 12, 25, 45, 60, 72], // Farmer’s real curve
        borderColor: "#3b82f6",
        backgroundColor: "#3b82f650",
        tension: 0.4,
      },
    ],
  };

  return (
    <div className="w-full">
      <Line data={data} />
    </div>
  );
}
