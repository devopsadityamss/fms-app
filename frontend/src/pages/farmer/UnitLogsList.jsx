// src/pages/farmer/UnitLogsList.jsx

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";

export default function UnitLogsList() {
  const { unitId } = useParams();

  const [logs, setLogs] = useState([]);
  const [unitName, setUnitName] = useState("");
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadLogs = async () => {
    let toastId;

    try {
      toastId = toast.loading("Loading activity logs...");

      // fetch logs
      const res = await farmerApi.getUnitOperationLogs(unitId);
      setLogs(res.items || []);
      setTotal(res.total || 0);

      // fetch unit name
      const unit = await farmerApi.getProductionUnit(unitId);
      setUnitName(unit?.name || "Production Unit");

      toast.dismiss(toastId);
      toast.success("Logs loaded!");
    } catch (err) {
      console.error("Error loading unit logs:", err);
      toast.dismiss();
      toast.error("Failed to load logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [unitId]);

  if (loading) return <div className="p-6">Loading logs...</div>;

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          Activity Logs — {unitName}
        </h1>

        <Link
          to={`/farmer/production/unit/${unitId}/log`}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded shadow"
        >
          ✏️ Log New Activity
        </Link>
      </div>

      {/* LIST */}
      {logs.length === 0 ? (
        <div className="p-4 bg-gray-100 rounded text-gray-700">
          No activity logs yet. Start by adding one!
        </div>
      ) : (
        <div className="space-y-4">
          {logs.map((log) => (
            <LogCard key={log.id} log={log} unitId={unitId} />
          ))}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------
   LOG CARD COMPONENT
------------------------------------------------- */
function LogCard({ log, unitId }) {
  const displayDate = new Date(log.performed_on).toLocaleDateString();

  const stageTitle = log.stage?.title || "N/A";
  const taskTitle = log.task_template?.title || "N/A";

  return (
    <div className="bg-white shadow rounded p-4 space-y-3">

      {/* DATE + STATUS + LINK */}
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold text-lg">{displayDate}</div>
          <div className="text-sm text-gray-500">
            {log.status || "Pending"}
          </div>
        </div>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${log.id}`}
          className="text-blue-600 hover:underline text-sm"
        >
          View Details →
        </Link>
      </div>

      {/* STAGE + TASK */}
      <div className="text-gray-700 text-sm">
        <strong>Stage:</strong> {stageTitle} <br />
        <strong>Task:</strong> {taskTitle}
      </div>

      {/* NOTES */}
      {log.notes && (
        <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
          {log.notes}
        </div>
      )}

      {/* QUICK ACTION BUTTONS */}
      <div className="flex flex-wrap gap-2 pt-1">

        <Link
          to={`/farmer/production/unit/${unitId}/log/${log.id}/material`}
          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
        >
          ➕ Material
        </Link>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${log.id}/labour`}
          className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm"
        >
          👷 Labour
        </Link>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${log.id}/expense`}
          className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1 rounded text-sm"
        >
          💰 Expense
        </Link>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${log.id}/media`}
          className="bg-gray-700 hover:bg-gray-800 text-white px-3 py-1 rounded text-sm"
        >
          📷 Media
        </Link>
      </div>
    </div>
  );
}
