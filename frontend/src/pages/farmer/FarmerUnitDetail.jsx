// frontend/src/pages/farmer/FarmerUnitDetail.jsx

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { farmerApi } from "../../api/farmer";
import { CheckCircleIcon } from "@heroicons/react/24/solid";

/**
 * FarmerUnitDetail
 *
 * - Loads full production unit (stages + tasks)
 * - Allows marking tasks complete
 * - Allows adding stages (inline form)
 * - Allows adding tasks to a specific stage (inline form per stage)
 *
 * Notes:
 * - Uses farmerApi.getProductionUnit, farmerApi.completeTask,
 *   farmerApi.addTaskToStage, farmerApi.updateProductionUnit
 * - If backend doesn't implement updateProductionUnit/addTaskToStage,
 *   the UI will still try but will surface the error.
 */

export default function FarmerUnitDetail() {
  const { unitId } = useParams();
  const navigate = useNavigate();

  const [unit, setUnit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshToggle, setRefreshToggle] = useState(false);

  // Add stage form state
  const [showAddStage, setShowAddStage] = useState(false);
  const [newStageTitle, setNewStageTitle] = useState("");
  const [newStageOrder, setNewStageOrder] = useState(1);
  const [addingStage, setAddingStage] = useState(false);

  // Per-stage add-task UI state (map stageId -> boolean)
  const [taskFormVisible, setTaskFormVisible] = useState({});
  const [taskFormValues, setTaskFormValues] = useState({}); // stageId -> { title, due_date, priority }

  useEffect(() => {
    if (!unitId) return;
    setLoading(true);

    farmerApi
      .getProductionUnit(unitId)
      .then((res) => {
        setUnit(res);
      })
      .catch((err) => {
        console.error("Unit detail fetch error:", err);
      })
      .finally(() => setLoading(false));
  }, [unitId, refreshToggle]);

  // Refresh helper
  const refresh = () => setRefreshToggle((s) => !s);

  // MARK TASK COMPLETE
  const handleCompleteTask = async (taskId) => {
    try {
      await farmerApi.completeTask(taskId);
      // optimistic refresh
      refresh();
    } catch (err) {
      console.error("Failed completing task:", err);
      alert("Failed to complete task.");
    }
  };

  // ADD STAGE
  const handleAddStage = async () => {
    if (!newStageTitle.trim()) {
      alert("Stage title required");
      return;
    }
    if (!unit) {
      alert("Unit not loaded");
      return;
    }

    setAddingStage(true);

    // Basic optimistic UI: build new stage object local id
    const tempId = `temp-${Date.now()}`;
    const stageObj = {
      id: tempId,
      unit_id: unit.id,
      title: newStageTitle,
      order: Number(newStageOrder) || (unit.stages?.length + 1) || 1,
      tasks: [],
    };

    try {
      // Optimistically update UI
      setUnit((u) => ({
        ...u,
        stages: [...(u.stages || []), stageObj],
      }));
      setNewStageTitle("");
      setNewStageOrder((prev) => prev + 1);
      setShowAddStage(false);

      // Backend call — updateProductionUnit should accept payload to add stage
      // If your backend implements a dedicated endpoint, replace with that.
      const payload = {
        add_stage: {
          title: stageObj.title,
          order: stageObj.order,
        },
      };

      await farmerApi.updateProductionUnit(unit.id, payload);

      // Refresh to pick up server-assigned IDs and consistent data
      refresh();
    } catch (err) {
      console.error("Add stage failed:", err);
      alert("Failed to add stage.");
      // rollback optimistic update
      refresh();
    } finally {
      setAddingStage(false);
    }
  };

  // SHOW / HIDE task form per stage
  const toggleTaskForm = (stageId) => {
    setTaskFormVisible((s) => ({ ...s, [stageId]: !s[stageId] }));
    setTaskFormValues((v) => ({
      ...v,
      [stageId]: v[stageId] || { title: "", due_date: "", priority: "" },
    }));
  };

  const handleTaskInputChange = (stageId, field, value) => {
    setTaskFormValues((v) => ({
      ...v,
      [stageId]: { ...(v[stageId] || {}), [field]: value },
    }));
  };

  // ADD TASK TO STAGE
  const handleAddTask = async (stage) => {
    const vals = taskFormValues[stage.id] || {};
    if (!vals.title || !vals.title.trim()) {
      alert("Task title required");
      return;
    }

    // Build payload expected by addTaskToStage
    const payload = {
      title: vals.title,
      order: stage.tasks?.length ? stage.tasks.length + 1 : 1,
      due_date: vals.due_date || null,
      priority: vals.priority || null,
    };

    // optimistic UI: push task with temp id
    const tempTask = {
      id: `temp-task-${Date.now()}`,
      stage_id: stage.id,
      title: payload.title,
      order: payload.order,
      completed: false,
      due_date: payload.due_date,
      priority: payload.priority,
    };

    try {
      // optimistic local update
      setUnit((u) => ({
        ...u,
        stages: u.stages.map((s) =>
          s.id === stage.id ? { ...s, tasks: [...(s.tasks || []), tempTask] } : s
        ),
      }));

      // call backend
      await farmerApi.addTaskToStage(stage.id, payload);

      // refresh from server
      refresh();

      // hide task form
      setTaskFormVisible((s) => ({ ...s, [stage.id]: false }));
    } catch (err) {
      console.error("Add task failed:", err);
      alert("Failed to add task.");
      // rollback by refreshing
      refresh();
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-gray-500">Loading production unit details...</div>
    );
  }

  if (!unit) {
    return <div className="p-6 text-red-600">Production unit not found.</div>;
  }

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="bg-white p-6 shadow rounded-xl flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{unit.name}</h1>
          <p className="text-gray-600 mt-1">
            {unit.practice_type} • {unit.category || "General"}
          </p>

          <div className="mt-3 flex gap-6 text-sm">
            <div>
              <span className="font-semibold">Progress:</span>{" "}
              {unit.progress ?? 0}%
            </div>
            <div>
              <span className="font-semibold">Status:</span>{" "}
              {unit.status || "Pending"}
            </div>
            <div>
              <span className="font-semibold">Health:</span>{" "}
              {unit.health_status || "N/A"}
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            className="px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            onClick={() => navigate("/farmer/dashboard")}
          >
            Back to Dashboard
          </button>

          <button
            className="px-3 py-1 bg-emerald-600 text-white rounded-md hover:bg-emerald-700"
            onClick={() => setShowAddStage((s) => !s)}
          >
            {showAddStage ? "Cancel Add Stage" : "+ Add Stage"}
          </button>
        </div>
      </div>

      {/* Add Stage Form (inline) */}
      {showAddStage && (
        <div className="bg-white p-4 rounded-xl shadow">
          <h3 className="font-semibold mb-2">Create New Stage</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              className="border rounded p-2 col-span-2"
              placeholder="Stage title (e.g., Soil Test)"
              value={newStageTitle}
              onChange={(e) => setNewStageTitle(e.target.value)}
            />
            <input
              className="border rounded p-2"
              type="number"
              min={1}
              value={newStageOrder}
              onChange={(e) => setNewStageOrder(e.target.value)}
              placeholder="Order"
            />
          </div>

          <div className="mt-3">
            <button
              className={`px-4 py-2 rounded text-white ${
                addingStage ? "bg-gray-400" : "bg-indigo-600 hover:bg-indigo-700"
              }`}
              onClick={handleAddStage}
              disabled={addingStage}
            >
              {addingStage ? "Adding..." : "Add Stage"}
            </button>
          </div>
        </div>
      )}

      {/* Stages list */}
      <div className="space-y-6">
        {(unit.stages || []).length === 0 && (
          <div className="bg-white p-6 rounded-xl shadow text-gray-500">
            No stages defined for this unit yet.
          </div>
        )}

        {(unit.stages || []).map((stage) => (
          <div key={stage.id} className="bg-white p-6 rounded-xl shadow">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold">
                  {stage.order}. {stage.title}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  {stage.tasks?.length || 0} task
                  {stage.tasks?.length === 1 ? "" : "s"}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => toggleTaskForm(stage.id)}
                  className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                >
                  {taskFormVisible[stage.id] ? "Cancel" : "+ Add Task"}
                </button>
              </div>
            </div>

            {/* Task list */}
            <div className="mt-4 space-y-3">
              {stage.tasks?.length === 0 ? (
                <div className="text-gray-400 italic">No tasks for this stage.</div>
              ) : (
                stage.tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-4 rounded-lg border flex justify-between items-center ${
                      task.completed
                        ? "bg-green-50 border-green-300"
                        : "bg-gray-50 border-gray-300"
                    }`}
                  >
                    <div>
                      <p className="font-medium">{task.title}</p>
                      {task.due_date && (
                        <p className="text-xs text-gray-500">
                          Due: {new Date(task.due_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      {!task.completed ? (
                        <button
                          onClick={() => handleCompleteTask(task.id)}
                          className="px-3 py-1 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 text-sm"
                        >
                          Mark Done
                        </button>
                      ) : (
                        <CheckCircleIcon className="w-6 h-6 text-emerald-600" />
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Inline add task form */}
            {taskFormVisible[stage.id] && (
              <div className="mt-4 border-t pt-4">
                <h4 className="text-sm font-semibold mb-2">New Task</h4>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <input
                    className="col-span-2 border rounded p-2"
                    placeholder="Task title"
                    value={(taskFormValues[stage.id]?.title) || ""}
                    onChange={(e) =>
                      handleTaskInputChange(stage.id, "title", e.target.value)
                    }
                  />
                  <input
                    type="date"
                    className="border rounded p-2"
                    value={(taskFormValues[stage.id]?.due_date) || ""}
                    onChange={(e) =>
                      handleTaskInputChange(stage.id, "due_date", e.target.value)
                    }
                  />
                </div>

                <div className="mt-3 flex gap-3">
                  <select
                    className="border rounded p-2"
                    value={(taskFormValues[stage.id]?.priority) || ""}
                    onChange={(e) =>
                      handleTaskInputChange(stage.id, "priority", e.target.value)
                    }
                  >
                    <option value="">Priority</option>
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                  </select>

                  <button
                    className="px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    onClick={() => handleAddTask(stage)}
                  >
                    Add Task
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
