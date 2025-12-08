// frontend/src/pages/farmer/FarmerDashboard.jsx
import React, { useEffect, useState } from "react";
import { useUser } from "../../context/UserContext";
import { farmerApi } from "../../api/farmer";

// Components
import KPIBlock from "../../components/farmer/KPIBlock";
import ProductionUnitCard from "../../components/farmer/ProductionUnitCard";

import ProductionMixPie from "../../components/farmer/charts/ProductionMixPie";
import CostDistributionPie from "../../components/farmer/charts/CostDistributionPie";
import ProgressLineChart from "../../components/farmer/charts/ProgressLineChart";

export default function FarmerDashboard() {
  const { supabaseUser } = useUser();
  const [summary, setSummary] = useState(null);
  const [units, setUnits] = useState([]);

  useEffect(() => {
    if (!supabaseUser?.id) return;

    // Load dashboard summary
    farmerApi
      .getDashboardSummary(supabaseUser.id)
      .then((res) => setSummary(res))
      .catch((err) => console.error("Dashboard summary error:", err));

    // Load production units
    farmerApi
      .listProductionUnits(supabaseUser.id)
      .then((res) => setUnits(res || []))
      .catch((err) => console.error("Fetch units error:", err));
  }, [supabaseUser]);

  return (
    <div className="p-6 space-y-10">

      {/* ======================================== */}
      {/* 1) KPI BANNER */}
      {/* ======================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-6">
        <KPIBlock title="Total Units" value={summary?.total_units || 0} />
        <KPIBlock title="Active Units" value={summary?.active_units || 0} />
        <KPIBlock title="Upcoming Tasks" value={summary?.upcoming_tasks || 0} />
        <KPIBlock title="Overdue Tasks" value={summary?.overdue_tasks || 0} />
        <KPIBlock
          title="Total Expenses"
          value={`₹${summary?.total_expenses || 0}`}
        />
        <KPIBlock
          title="Profit Index"
          value={`${summary?.profit_index || 0}%`}
        />
      </div>

      {/* ======================================== */}
      {/* 2) ANALYTICS ROW (CHARTS) */}
      {/* ======================================== */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Production Mix</h3>
          <ProductionMixPie />
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Cost Distribution</h3>
          <CostDistributionPie />
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Cycle Progress</h3>
          <ProgressLineChart />
        </div>
      </div>

      {/* ======================================== */}
      {/* 3) PRODUCTION UNITS LIST */}
      {/* ======================================== */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Your Production Units</h2>

          <button
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-700"
            onClick={() => (window.location.href = "/farmer/units/new")}
          >
            + Create Unit
          </button>
        </div>

        {units.length === 0 ? (
          <p className="text-gray-500 mt-2">No production units yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {units.map((u) => (
              <ProductionUnitCard key={u.id} unit={u} />
            ))}
          </div>
        )}
      </div>

      {/* ======================================== */}
      {/* 4) SMART SUGGESTIONS */}
      {/* ======================================== */}
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Smart Suggestions</h3>

        <ul className="space-y-3 text-gray-700">
          <li>🌧 Rain expected soon — irrigation schedule may need adjustment.</li>
          <li>📉 Tomato prices are volatile — consider storage options.</li>
          <li>🧪 Soil test older than 6 months — renewal suggested.</li>
          <li>🌾 High demand for onions upcoming season — good planting window.</li>
        </ul>
      </div>

      {/* ======================================== */}
      {/* 5) QUICK ACTIONS */}
      {/* ======================================== */}
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>

        <div className="flex flex-wrap gap-4">
          <button className="px-4 py-2 rounded bg-emerald-600 text-white shadow">
            Add Expense
          </button>
          <button className="px-4 py-2 rounded bg-blue-600 text-white shadow">
            Add Task
          </button>
          <button className="px-4 py-2 rounded bg-orange-600 text-white shadow">
            Hire Worker
          </button>
          <button className="px-4 py-2 rounded bg-purple-600 text-white shadow">
            Book Service Provider
          </button>
        </div>
      </div>
    </div>
  );
}
