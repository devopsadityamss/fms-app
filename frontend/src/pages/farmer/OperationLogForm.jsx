// src/pages/farmer/OperationLogForm.jsx

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";

export default function OperationLogForm() {
  const { unitId } = useParams();
  const navigate = useNavigate();

  const [unit, setUnit] = useState(null);
  const [stageId, setStageId] = useState("");
  const [taskId, setTaskId] = useState("");

  const [performedOn, setPerformedOn] = useState(
    () => new Date().toISOString().split("T")[0]
  );

  const [quantity, setQuantity] = useState("");
  const [unitValue, setUnitValue] = useState("");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  /* ----------------------------------------------------
     LOAD UNIT DETAILS (Stages + Tasks)
  ---------------------------------------------------- */
  const loadUnit = async () => {
    let toastId;
    try {
      toastId = toast.loading("Loading unit information...");
      const data = await farmerApi.getProductionUnit(unitId);

      setUnit(data || null);

      // Auto-select current active stage
      if (data?.active_stage_id) setStageId(data.active_stage_id);

      toast.dismiss(toastId);
      toast.success("Unit loaded!");
    } catch (err) {
      console.error("Error loading unit details:", err);
      toast.dismiss();
      toast.error("Failed to load unit details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUnit();
  }, [unitId]);

  /* ----------------------------------------------------
     FIND TASKS FOR SELECTED STAGE
  ---------------------------------------------------- */
  const tasksForStage =
    unit?.stages?.find((s) => s.id === stageId)?.tasks || [];

  /* ----------------------------------------------------
     ON SUBMIT
  ---------------------------------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!stageId) {
      toast.error("Please select a stage.");
      return;
    }
    if (!performedOn) {
      toast.error("Please select a valid date.");
      return;
    }

    const toastId = toast.loading("Saving activity...");

    setSaving(true);

    try {
      await farmerApi.createOperationLog({
        production_unit_id: unitId,
        stage_id: stageId,
        task_template_id: taskId || null,
        performed_on: performedOn,
        quantity: quantity ? Number(quantity) : null,
        unit: unitValue || null,
        notes: notes?.trim() || null
      });

      toast.dismiss(toastId);
      toast.success("Activity logged!");

      navigate(`/farmer/production/unit/${unitId}/logs`, { replace: true });

    } catch (err) {
      console.error("Error creating operation log:", err);
      toast.dismiss(toastId);
      toast.error("Failed to save activity.");
    } finally {
      setSaving(false);
    }
  };

  /* ----------------------------------------------------
     LOADING STATES
  ---------------------------------------------------- */
  if (loading) return <div className="p-6">Loading activity form...</div>;
  if (!unit) return <div className="p-6">Production unit not found.</div>;

  /* ----------------------------------------------------
     FORM UI
  ---------------------------------------------------- */
  return (
    <div className="p-6 max-w-xl mx-auto">

      {/* PAGE HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Log Activity</h1>

        <button
          className="text-blue-600 underline"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 shadow rounded">

        {/* STAGE SELECT */}
        <div>
          <label className="block text-sm font-semibold mb-1">Stage</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={stageId}
            onChange={(e) => {
              setStageId(e.target.value);
              setTaskId(""); // reset task
            }}
            required
          >
            <option value="">Select Stage</option>
            {unit?.stages?.map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.title}
              </option>
            ))}
          </select>
        </div>

        {/* TASK SELECT */}
        <div>
          <label className="block text-sm font-semibold mb-1">Task (Optional)</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
          >
            <option value="">No Task</option>
            {tasksForStage.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title}
              </option>
            ))}
          </select>
        </div>

        {/* DATE */}
        <div>
          <label className="block text-sm font-semibold mb-1">Performed On</label>
          <input
            type="date"
            className="w-full border rounded px-3 py-2"
            value={performedOn}
            onChange={(e) => setPerformedOn(e.target.value)}
            required
          />
        </div>

        {/* QUANTITY + UNIT */}
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-sm font-semibold mb-1">Quantity</label>
            <input
              type="number"
              step="0.1"
              className="w-full border rounded px-3 py-2"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Unit</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              placeholder="kg / liters / hrs"
              value={unitValue}
              onChange={(e) => setUnitValue(e.target.value)}
            />
          </div>
        </div>

        {/* NOTES */}
        <div>
          <label className="block text-sm font-semibold mb-1">Notes</label>
          <textarea
            rows="3"
            className="w-full border rounded px-3 py-2"
            placeholder="Add extra details..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        {/* SUBMIT BUTTON */}
        <button
          type="submit"
          disabled={saving}
          className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded shadow disabled:bg-gray-400"
        >
          {saving ? "Saving..." : "Submit Activity Log"}
        </button>
      </form>
    </div>
  );
}
