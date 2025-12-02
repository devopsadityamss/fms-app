import React, { useEffect, useState } from "react";
import SlideOver from "./SlideOver";
import { api } from "../api/client";

export default function EditTaskPanel({ open, onClose, task, onUpdated }) {
  const [projects, setProjects] = useState([]);

  const [title, setTitle] = useState(task?.title || "");
  const [description, setDescription] = useState(task?.description || "");
  const [status, setStatus] = useState(task?.status || "pending");
  const [priority, setPriority] = useState(task?.priority || 1);
  const [projectId, setProjectId] = useState(task?.project_id || "");

  useEffect(() => {
    if (task) {
      setTitle(task.title);
      setDescription(task.description);
      setStatus(task.status);
      setPriority(task.priority);
      setProjectId(task.project_id);
    }
  }, [task]);

  useEffect(() => {
    api.get("/projects")
      .then((res) => setProjects(res.data))
      .catch(() => {});
  }, []);

  const updateTask = () => {
    api
      .put(`/tasks/${task.id}`, {
        title,
        description,
        status,
        priority,
        project_id: projectId,
      })
      .then((res) => {
        onUpdated(res.data);
        onClose();
      })
      .catch((err) => console.error(err));
  };

  if (!task) return null;

  return (
    <SlideOver open={open} onClose={onClose} title="Edit Task">
      <div className="space-y-4">

        {/* Project */}
        <div>
          <label className="block text-sm mb-1">Project</label>
          <select
            className="w-full p-2 border rounded"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm mb-1">Title</label>
          <input
            type="text"
            className="w-full p-2 border rounded"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm mb-1">Description</label>
          <textarea
            className="w-full p-2 border rounded"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          ></textarea>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm mb-1">Status</label>
          <select
            className="w-full p-2 border rounded"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm mb-1">Priority</label>
          <select
            className="w-full p-2 border rounded"
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
          >
            {[1,2,3,4,5].map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <button
          onClick={updateTask}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Save Changes
        </button>
      </div>
    </SlideOver>
  );
}
