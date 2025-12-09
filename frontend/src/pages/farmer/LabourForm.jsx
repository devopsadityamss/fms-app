// src/pages/farmer/LabourForm.jsx

import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";

export default function LabourForm() {
  const { unitId, logId } = useParams();
  const navigate = useNavigate();

  const [workerName, setWorkerName] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [hours, setHours] = useState("");
  const [labourCost, setLabourCost] = useState("");
  const [role, setRole] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  /* -----------------------------------------
     SUBMIT LABOUR USAGE
  ----------------------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (hours && Number(hours) < 0) {
      toast.error("Hours worked cannot be negative.");
      return;
    }

    if (labourCost && Number(labourCost) < 0) {
      toast.error("Cost cannot be negative.");
      return;
    }

    const toastId = toast.loading("Saving labour usage...");
    setSaving(true);

    try {
      await farmerApi.addLabourUsage({
        operation_log_id: logId,
        worker_name: workerName || null,
        worker_id: workerId || null,
        hours: hours ? Number(hours) : null,
        labour_cost: labourCost ? Number(labourCost) : null,
        role: role || null,
        extra: notes ? { notes } : null,
      });

      toast.dismiss(toastId);
      toast.success("Labour usage saved!");

      navigate(`/farmer/production/unit/${unitId}/log/${logId}`);
    } catch (err) {
      console.error("Error adding labour usage:", err);
      toast.dismiss(toastId);
      toast.error("Failed to save labour usage.");
    } finally {
      setSaving(false);
    }
  };

  /* -----------------------------------------
     UI
  ----------------------------------------- */
  return (
    <div className="p-6 max-w-xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Add Labour Usage</h1>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${logId}`}
          className="text-blue-600 underline"
        >
          ← Back
        </Link>
      </div>

      {/* FORM CARD */}
      <div className="bg-white p-6 rounded shadow">
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Worker Name */}
          <div>
            <label className="block text-sm font-semibold mb-1">Worker Name</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={workerName}
              onChange={(e) => setWorkerName(e.target.value)}
              placeholder="John, Farmhand team, etc."
            />
          </div>

          {/* Worker ID */}
          <div>
            <label className="block text-sm font-semibold mb-1">Worker ID (Optional)</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={workerId}
              onChange={(e) => setWorkerId(e.target.value)}
              placeholder="Internal worker reference"
            />
          </div>

          {/* Hours & Cost */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-semibold mb-1">Hours Worked</label>
              <input
                type="number"
                step="0.1"
                className="w-full border rounded px-3 py-2"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="2.5"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1">Cost (₹)</label>
              <input
                type="number"
                step="0.1"
                className="w-full border rounded px-3 py-2"
                value={labourCost}
                onChange={(e) => setLabourCost(e.target.value)}
                placeholder="300"
              />
            </div>
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-semibold mb-1">Role</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="Ploughing, Harvesting, Irrigation..."
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-semibold mb-1">Notes</label>
            <textarea
              className="w-full border rounded px-3 py-2"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional additional details..."
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={saving}
            className={`w-full py-2 rounded shadow text-white ${
              saving
                ? "bg-purple-400 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {saving ? "Saving..." : "Save Labour Usage"}
          </button>

        </form>
      </div>
    </div>
  );
}
