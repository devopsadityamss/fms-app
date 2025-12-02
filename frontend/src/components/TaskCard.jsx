import React from "react";

export default function TaskCard({ task }) {
  return (
    <div
      className="p-4 bg-white rounded-lg border shadow-sm hover:shadow-md transition cursor-pointer"
      onClick={() => (window.location.href = `/task/${task.id}`)}
    >
      <h3 className="font-semibold text-sm mb-1">{task.title}</h3>
      {task.description && (
        <p className="text-xs text-slate-500 line-clamp-2">{task.description}</p>
      )}

      <div className="flex justify-between items-center mt-3">
        <span
          className={`text-xs px-2 py-1 rounded ${
            task.status === "completed"
              ? "bg-green-100 text-green-700"
              : task.status === "in_progress"
              ? "bg-yellow-100 text-yellow-700"
              : "bg-slate-100 text-slate-600"
          }`}
        >
          {task.status.replace("_", " ")}
        </span>

        <span className="text-xs text-slate-400">
          Priority {task.priority}
        </span>
      </div>
    </div>
  );
}
