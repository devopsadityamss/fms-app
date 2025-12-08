// src/pages/farmer/ProductionUnits/ProductionUnitView.jsx
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../../../services/api";

export default function ProductionUnitView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [unit, setUnit] = useState(null);
  const [loading, setLoading] = useState(true);

  // ---------------- FETCH UNIT ----------------
  const loadUnit = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/farmer/production-unit/${id}`);
      setUnit(res.data);
    } catch (err) {
      console.error(err);
      alert("Failed to load production unit");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) loadUnit();
  }, [id]);

  // ---------------- UPDATE TASK COMPLETION ----------------
  const toggleTaskCompletion = async (task) => {
    try {
      await api.put(`/farmer/production-unit/task/${task.id}`, {
        completed: !task.completed,
      });

      await loadUnit(); // refresh after update (backend recalculates progress)
    } catch (err) {
      console.error(err);
      alert("Failed to update task");
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (!unit) return <div className="p-8">Not found</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{unit.name}</h1>

          <div className="text-sm text-gray-600">
            {unit.practice_type} • {unit.category}
          </div>

          <div className="mt-1 text-sm">
            <span className="font-semibold">Progress:</span> {unit.progress || 0}%
          </div>

          <div className="mt-1 text-sm">
            <span className="font-semibold">Health:</span>{" "}
            <span className={
              unit.health_status === "excellent"
                ? "text-green-600"
                : unit.health_status === "warning"
                ? "text-yellow-600"
                : "text-red-600"
            }>
              {unit.health_status}
            </span>
          </div>
        </div>

        <button
          className="px-3 py-1 bg-gray-200 rounded"
          onClick={() => navigate(-1)}
        >
          Back
        </button>
      </div>

      {/* STAGES */}
      <div className="space-y-4">
        {unit.stages.map((s, idx) => (
          <div key={s.id} className="bg-white p-4 rounded shadow">
            {/* Stage Header */}
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-500">Stage {idx + 1}</div>
                <div className="text-lg font-semibold">{s.title}</div>

                <div className="text-sm mt-1">
                  <span className="font-medium">Progress:</span> {s.progress || 0}%
                </div>
              </div>

              <div className="text-sm text-gray-400">
                {s.tasks.length} tasks
              </div>
            </div>

            {/* Task List */}
            <ul className="mt-3 space-y-2">
              {s.tasks.map((t) => (
                <li
                  key={t.id}
                  className="flex items-center gap-3 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={t.completed}
                    onChange={() => toggleTaskCompletion(t)}
                    className="w-4 h-4"
                  />

                  <span
                    className={
                      t.completed
                        ? "line-through text-green-700"
                        : "text-gray-800"
                    }
                  >
                    {t.title}
                  </span>

                  {t.completed && (
                    <span className="text-green-600 ml-2">(Done)</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
