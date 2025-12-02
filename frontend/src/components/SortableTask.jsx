import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import TaskCard from "./TaskCard";

/**
 * SortableTask uses useSortable to make the task draggable.
 * It wraps the TaskCard UI and exposes drag listeners.
 */
export default function SortableTask({ id, task }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Put the drag handle/listeners on the root to make whole card draggable.
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TaskCard task={task} />
    </div>
  );
}
