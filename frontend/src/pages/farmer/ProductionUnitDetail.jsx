// src/pages/farmer/ProductionUnitDetail.jsx

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { farmerApi } from "../../api/farmer";

// ⭐ Toast notifications
import toast from "react-hot-toast";

export default function ProductionUnitDetail() {
  const { unitId } = useParams();
  const [unit, setUnit] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUnit = async () => {
    try {
      const res = await farmerApi.getProductionUnit(unitId);

      // ⭐ FIX: backend returns { ok:true, data:{...} }
      const data = res?.data;

      if (!data) {
        setUnit(null);
        toast.error("Failed to load unit data.");
      } else {
        setUnit(data);
      }
    } catch (err) {
      console.error("Error loading production unit:", err);
      toast.error("Failed to load unit details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUnit();
  }, [unitId]);

  if (loading) return <div className="p-6">Loading unit details...</div>;
  if (!unit) return <div className="p-6">Production unit not found.</div>;

  return (
    <div className="p-6 space-y-6">

      {/* HEADER */}
      <div className="bg-white shadow rounded p-4 space-y-3">

        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{unit.name}</h1>
          <StatusBadge status={unit.health_status} />
        </div>

        <div className="text-gray-600 text-sm">
          Practice Type: <strong>{unit.practice_type?.toUpperCase()}</strong>
        </div>

        {/* Progress */}
        <ProgressBar progress={unit.progress || 0} />

        {/* Quick Action Buttons */}
        <div className="flex flex-wrap gap-3 pt-2">
          <ActionButton to={`/farmer/production/unit/${unitId}/log`} color="green">
            ✏️ Log Activity
          </ActionButton>

          <ActionButton to={`/farmer/production/unit/${unitId}/logs`} color="blue">
            📘 View Logs
          </ActionButton>

          <ActionButton to={`/farmer/production/unit/${unitId}/expense`} color="yellow">
            💰 Add Expense
          </ActionButton>
        </div>

      </div>

      {/* ACTIVE STAGE */}
      <ActiveStageCard unit={unit} />

      {/* STAGES + TASKS */}
      <StageTaskList
        stages={unit.stages || []}
        unitId={unitId}
        reload={loadUnit}
      />
    </div>
  );
}

/* ----------------------------------------------
   ACTIVE STAGE COMPONENT
----------------------------------------------- */
function ActiveStageCard({ unit }) {
  if (!unit?.active_stage) return null;

  return (
    <div className="bg-green-50 border border-green-300 p-4 rounded">
      <h2 className="text-lg font-semibold">Current Stage</h2>
      <div className="mt-2 text-gray-700">
        <strong>{unit.active_stage.title}</strong>{" "}
        ({unit.active_stage_index + 1} of {unit.stages.length})
      </div>
    </div>
  );
}

/* ----------------------------------------------
   STAGE + TASK LIST WITH OVERDUE DETECTION
----------------------------------------------- */
function StageTaskList({ stages, unitId, reload }) {
  const today = new Date();

  return (
    <div className="space-y-6">
      {stages.map((stage) => {
        const sortedTasks = [...(stage.tasks || [])].sort((a, b) => {
          const aOver = isOverdue(a, today);
          const bOver = isOverdue(b, today);
          if (aOver && !bOver) return -1;
          if (!aOver && bOver) return 1;
          if (!a.completed && b.completed) return -1;
          if (a.completed && !b.completed) return 1;
          return 0;
        });

        return (
          <div key={stage.id} className="bg-white shadow rounded p-4">

            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-semibold">{stage.title}</h2>
              <span className="text-sm text-gray-500">
                {stage.tasks?.length || 0} tasks
              </span>
            </div>

            {sortedTasks.length === 0 ? (
              <div className="text-gray-500">No tasks added.</div>
            ) : (
              <ul className="space-y-2">
                {sortedTasks.map((task) => {
                  const overdue = isOverdue(task, today);

                  return (
                    <li
                      key={task.id}
                      className="border-b pb-2 last:border-none last:pb-0"
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-medium">{task.title}</span>

                          {overdue && !task.completed && (
                            <span className="ml-2 text-red-600 text-xs">
                              ⏰ Overdue
                            </span>
                          )}
                        </div>

                        {!task.completed && (
                          <button
                            className="text-green-600 hover:underline text-sm"
                            disabled={task._loading}
                            onClick={async () => {
                              try {
                                task._loading = true;
                                toast.loading("Completing task...");

                                await farmerApi.completeTask(task.id);

                                toast.dismiss();
                                toast.success("Task completed!");

                                await reload();
                              } catch (err) {
                                toast.dismiss();
                                toast.error("Could not complete task.");
                                console.error("Task completion error:", err);
                              } finally {
                                task._loading = false;
                              }
                            }}
                          >
                            {task._loading ? "..." : "Mark Done ✓"}
                          </button>
                        )}

                        {task.completed && (
                          <span className="text-xs text-gray-500">Completed ✔</span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ----------------------------------------------
   HELPER: CHECK OVERDUE
----------------------------------------------- */
function isOverdue(task, today) {
  if (!task.due_date || task.completed) return false;
  try {
    const due = new Date(task.due_date);
    return due < today;
  } catch {
    return false;
  }
}

/* ----------------------------------------------
   UI COMPONENTS
----------------------------------------------- */

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

function ProgressBar({ progress }) {
  return (
    <div className="mt-2">
      <div className="w-full bg-gray-200 rounded h-2">
        <div
          className="h-2 rounded bg-green-600"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      <div className="text-xs text-gray-500 mt-1">{progress}% complete</div>
    </div>
  );
}

function ActionButton({ to, color, children }) {
  const colors = {
    green: "bg-green-600 hover:bg-green-700",
    blue: "bg-blue-600 hover:bg-blue-700",
    yellow: "bg-yellow-500 hover:bg-yellow-600",
  };

  return (
    <Link
      to={to}
      className={`${colors[color]} text-white px-3 py-2 rounded shadow text-sm`}
    >
      {children}
    </Link>
  );
}
