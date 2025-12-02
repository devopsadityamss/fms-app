import React, { useEffect, useState } from "react";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, rectSortingStrategy } from "@dnd-kit/sortable";
import Column from "../components/KanbanColumn";
import CreateTaskPanel from "../components/CreateTaskPanel";

/**
 * TaskBoard with DnD persistence.
 * - Drag a task card and drop it into a column (status).
 * - On drop, do an optimistic UI change and call PUT /tasks/:id { status: newStatus }.
 * - If API fails, refetch tasks.
 */

function useQuery() {
  return new URLSearchParams(window.location.search);
}

export default function TaskBoard() {
  const q = useQuery();
  const project_id = q.get("project_id");

  const [tasks, setTasks] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);

  const loadTasks = () => {
    api
      .get("/tasks", { params: project_id ? { project_id } : {} })
      .then((res) => setTasks(res.data))
      .catch(() => {});
  };

  useEffect(() => {
    loadTasks();
  }, [project_id]);

  const columns = {
    pending: tasks.filter((t) => t.status === "pending"),
    in_progress: tasks.filter((t) => t.status === "in_progress"),
    completed: tasks.filter((t) => t.status === "completed"),
  };

  const sensors = useSensors(useSensor(PointerSensor));

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over) return;

    const taskId = active.id;
    const newStatus = over.id; // we set column element id to status

    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;
    if (task.status === newStatus) return;

    // Optimistic update
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)));

    // Persist change
    api
      .put(`/tasks/${taskId}`, { status: newStatus })
      .then(() => {
        // success; nothing else needed since we already updated UI
      })
      .catch((err) => {
        console.error("Failed to persist task status:", err);
        // rollback by reloading tasks
        loadTasks();
      });
  };

  return (
    <MainLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Task Board</h1>

        <button
          onClick={() => setCreateOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          + New Task
        </button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <div className="grid md:grid-cols-3 gap-6">
          {Object.entries(columns).map(([status, list]) => (
            <SortableContext key={status} items={list.map((t) => t.id)} strategy={rectSortingStrategy}>
              {/* Column expects `id` attribute on the drop area equal to status */}
              <Column id={status} title={status.replace("_", " ")} tasks={list} />
            </SortableContext>
          ))}
        </div>
      </DndContext>

      <CreateTaskPanel
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => loadTasks()}
        projectId={project_id}
      />
    </MainLayout>
  );
}
