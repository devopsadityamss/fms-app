import React, { useState } from "react";
import SlideOver from "./SlideOver";
import { api } from "../api/client";

export default function CreateProjectPanel({ open, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const createProject = () => {
    if (!name.trim()) return;

    api
      .post("/projects", { name, description })
      .then((res) => {
        onCreated(res.data); // Update parent list
        onClose();
        setName("");
        setDescription("");
      })
      .catch((err) => console.error(err));
  };

  return (
    <SlideOver open={open} onClose={onClose} title="Create Project">
      <div className="space-y-4">
        {/* Project Name */}
        <div>
          <label className="block text-sm font-medium mb-1">Project Name</label>
          <input
            type="text"
            className="w-full p-2 border rounded"
            placeholder="e.g., Website Redesign"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            className="w-full p-2 border rounded"
            rows={3}
            placeholder="Optional description..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <button
          onClick={createProject}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Create Project
        </button>
      </div>
    </SlideOver>
  );
}
