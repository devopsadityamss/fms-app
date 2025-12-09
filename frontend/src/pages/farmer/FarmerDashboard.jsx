// src/pages/farmer/FarmerDashboard.jsx
import React, { useEffect, useState } from "react";
import { useUser } from "../../context/UserContext";
import { api } from "../../services/api";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";

export default function FarmerDashboard() {
  const { supabaseUser } = useUser();
  const userId = supabaseUser?.id;

  const [summary, setSummary] = useState(null);
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadData = async () => {
    if (!userId) return;

    setLoading(true);
    setError(false);

    try {
      toast.loading("Loading dashboard...");

      const [summaryRes, unitsRes] = await Promise.all([
        api.get(`/farmer/production-unit/summary/${userId}`),
        api.get(`/farmer/production-unit/list/${userId}`)
      ]);

      toast.dismiss();

      // ⭐ FIX — backend returns { ok:true, data: {...} }
      setSummary(summaryRes.data?.data || {});
      setUnits(unitsRes.data?.data?.units || []);

      toast.success("Dashboard updated!");
    } catch (err) {
      toast.dismiss();
      toast.error("Failed to load dashboard.");
      console.error("Dashboard load error:", err);

      setSummary({});
      setUnits([]);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [userId]);

  if (loading)
    return <div className="p-6 text-gray-600 text-lg">⏳ Loading dashboard...</div>;

  if (error)
    return (
      <div className="p-6">
        <div className="bg-red-100 text-red-700 p-4 rounded mb-3">
          ❌ Failed to load dashboard
        </div>
        <button
          onClick={loadData}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          🔄 Retry
        </button>
      </div>
    );

  return (
    <div className="p-6 space-y-6">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Farmer Dashboard</h1>

        <Link
          to="/farmer/production/create"
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded shadow"
        >
          ➕ Create Production Unit
        </Link>
      </div>

      {/* SUMMARY CARDS */}
      {summary && (
        <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4">
          <SummaryCard title="Total Units" value={summary.total_units || 0} />
          <SummaryCard title="Active Units" value={summary.active_units || 0} />
          <SummaryCard title="Upcoming Tasks" value={summary.upcoming_tasks || 0} />

          <SummaryCard
            title="Overdue Tasks"
            value={summary.overdue_tasks || 0}
            highlight={summary.overdue_tasks > 0}
          />

          <SummaryCard
            title="Total Expenses"
            value={`₹${summary.total_expenses || 0}`}
          />

          <SummaryCard
            title="Profit Index"
            value={summary.profit_index || 0}
          />
        </div>
      )}

      {/* UNIT LIST */}
      <div>
        <h2 className="text-xl font-semibold mb-3">Your Production Units</h2>

        {units.length === 0 ? (
          <div className="p-4 bg-gray-100 rounded text-gray-700">
            No production units found. Start by creating one!
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {units.map((u) => (
              <UnitCard key={u.id} unit={u} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------ COMPONENTS ------------------ */

function SummaryCard({ title, value, highlight = false }) {
  return (
    <div
      className={`bg-white shadow rounded p-4 ${
        highlight ? "border border-red-400" : ""
      }`}
    >
      <div className="text-sm text-gray-600 flex justify-between">
        {title}
        {highlight && <span className="text-red-600 text-xs font-semibold">⚠️</span>}
      </div>

      <div className={`text-2xl font-bold mt-2 ${highlight ? "text-red-600" : ""}`}>
        {value}
      </div>
    </div>
  );
}

function UnitCard({ unit }) {
  return (
    <div className="block bg-white shadow rounded p-4 hover:shadow-md transition">

      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">{unit.name}</h3>
        <StatusBadge status={unit.health_status} />
      </div>

      <div className="text-gray-600 text-sm mt-1">
        {unit.practice_type?.toUpperCase()}
      </div>

      <div className="mt-3">
        <div className="w-full bg-gray-200 rounded h-2">
          <div
            className="h-2 rounded bg-green-600"
            style={{ width: `${unit.progress || 0}%` }}
          />
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {unit.progress || 0}% complete
        </div>
      </div>

      <div className="mt-3 text-sm">
        <strong>Next Task:</strong>{" "}
        {unit.next_task ? unit.next_task : "All tasks completed 🎉"}
      </div>

      {unit.overdue_count > 0 && (
        <div className="mt-2 text-sm text-red-600 font-medium">
          ⏰ {unit.overdue_count} overdue task
          {unit.overdue_count > 1 ? "s" : ""}
        </div>
      )}

      <div className="mt-4 space-y-2">
        <Link
          to={`/farmer/production/unit/${unit.id}`}
          className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded"
        >
          📄 View Unit
        </Link>

        <Link
          to={`/farmer/production/unit/${unit.id}/log`}
          className="block w-full text-center bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded"
        >
          ✏️ Log Activity
        </Link>

        <Link
          to={`/farmer/production/unit/${unit.id}/logs`}
          className="block w-full text-center bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded"
        >
          📘 View Logs
        </Link>

        <Link
          to={`/farmer/production/unit/${unit.id}/expense`}
          className="block w-full text-center bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-2 rounded"
        >
          💰 Add Expense
        </Link>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  let color = "bg-gray-400";

  if (status === "excellent") color = "bg-green-600";
  else if (status === "good") color = "bg-blue-600";
  else if (status === "warning") color = "bg-yellow-500";
  else if (status === "critical") color = "bg-red-600";

  return (
    <span className={`text-white text-xs px-2 py-1 rounded ${color}`}>
      {status || "unknown"}
    </span>
  );
}
