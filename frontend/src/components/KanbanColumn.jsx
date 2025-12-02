import React from "react";
import SortableTask from "./SortableTask";

/**
 * KanbanColumn
 * - The dropable area has an element with `id={id}` so dnd-kit uses it as `over.id`.
 * - Render list of SortableTask components
 */
export default function Column({ id, title, tasks = [] }) {
  return (
    <div className="bg-slate-50 p-3 rounded">
      <h3 className="font-semibold mb-3 capitalize">{title}</h3>

      {/* this div provides the id that becomes over.id in dnd */}
      <div id={id} className="space-y-3 min-h-[60px]">
        {tasks.map((task) => (
          <SortableTask key={task.id} id={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}
