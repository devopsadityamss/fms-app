import React, { useEffect, useState } from "react";
import SlideOver from "./SlideOver";
import { api } from "../api/client";

export default function CreateTaskPanel({ open, onClose, onCreated, projectId }) {
  const [projects, setProjects] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("pending");
  const [priority, setPriority] = useState(1);
  const [selectedProject, setSelectedProject] = useState(projectId || "");

  useEffect(() => {
    api.get("/projects")
      .then((res) => setProjects(res.data))
      .catch(() => {});
  }, []);

  const createTask = () => {
    if (!title.trim() || !selectedProject) return;

    api.post("/tasks", {
      title,
      description,
      status,
      priority,
      project_id: selectedProject,
    })
    .then((res) => {
      onCreated(res.data);
      onClose();

      // Reset form
      setTitle("");
      setDescription("");
      setStatus("pending");
      setPriority(1);
    })
    .catch((err) => console.error(err));
  };

  return (
    <SlideOver open={open} onClose={onClose} title="Create Task">
      <div className="space-y-4">

        {/* Project Selector */}
        {!projectId && (
          <div>
            <label className="block text-sm mb-1">Project</label>
            <select
              className="w-full p-2 border rounded"
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
            >
              <option value="">Select a project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Title */}
        <div>
          <label className="block text-sm mb-1">Title</label>
          <input
            type="text"
            className="w-full p-2 border rounded"
            placeholder="Task title..."
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
            placeholder="Optional description..."
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

        {/* Create Button */}
        <button
          onClick={createTask}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Create Task
        </button>
      </div>
    </SlideOver>
  );
}
