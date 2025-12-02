import React, { useState } from "react";

export default function TaskMeta({ task, onUpdate }) {
  const [status, setStatus] = useState(task.status);
  const [priority, setPriority] = useState(task.priority);

  const statusOptions = [
    { value: "pending", label: "Pending" },
    { value: "in_progress", label: "In Progress" },
    { value: "completed", label: "Completed" },
  ];

  const priorityOptions = [1, 2, 3, 4, 5];

  const updateStatus = (value) => {
    setStatus(value);
    onUpdate({ status: value });
  };

  const updatePriority = (value) => {
    setPriority(value);
    onUpdate({ priority: value });
  };

  return (
    <div className="bg-white p-4 rounded shadow w-64">
      <h3 className="font-semibold text-lg mb-4">Task Metadata</h3>

      {/* Status */}
      <div className="mb-4">
        <label className="block text-sm text-slate-600 mb-1">Status</label>
        <select
          value={status}
          onChange={(e) => updateStatus(e.target.value)}
          className="w-full p-2 rounded border"
        >
          {statusOptions.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Priority */}
      <div className="mb-4">
        <label className="block text-sm text-slate-600 mb-1">Priority</label>
        <select
          value={priority}
          onChange={(e) => updatePriority(e.target.value)}
          className="w-full p-2 rounded border"
        >
          {priorityOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>

      {/* Static fields for now (you can extend later) */}
      <div className="text-sm text-slate-600 mt-4">
        <p><strong>Assignee:</strong> {task.assignee_id || "None"}</p>
        <p><strong>Reporter:</strong> {task.reporter_id || "None"}</p>
        <p><strong>Due Date:</strong> {task.due_date || "Not set"}</p>
      </div>
    </div>
  );
}
