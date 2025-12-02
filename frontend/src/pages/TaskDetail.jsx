import React, { useEffect, useState } from "react";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { useParams } from "react-router-dom";

import TaskMeta from "../components/TaskMeta";
import TaskTimeline from "../components/TaskTimeline";
import TaskComments from "../components/TaskComments";
import EditTaskPanel from "../components/EditTaskPanel";   // ← ADDED
import ConfirmDialog from "../components/ConfirmDialog";   // ← ADDED
import { useNavigate } from "react-router-dom";             // ← ADDED

export default function TaskDetail() {
  const { id } = useParams();
  const navigate = useNavigate();                            // ← ADDED
  const [task, setTask] = useState(null);
  const [editOpen, setEditOpen] = useState(false);           // ← ADDED
  const [deleteOpen, setDeleteOpen] = useState(false);      // ← ADDED

  // demo data for timeline & comments
  const [timeline, setTimeline] = useState([
    { title: "Task created", description: "Initial creation", created_at: new Date() },
  ]);

  const [comments, setComments] = useState([]);

  useEffect(() => {
    api.get(`/tasks/${id}`)
      .then((res) => setTask(res.data))
      .catch(() => {});
  }, [id]);

  const updateTask = (patch) => {
    api.put(`/tasks/${id}`, patch)
      .then((res) => setTask(res.data))
      .catch(() => {});
  };

  const addComment = (text) => {
    setComments([{ text }, ...comments]);
  };

  if (!task) {
    return (
      <MainLayout>
        <p>Loading...</p>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="flex gap-6">
        {/* Main Content */}
        <div className="flex-1 space-y-6">
          <h1 className="text-3xl font-bold">{task.title}</h1>

          {/* Edit Button */}
          <button
            onClick={() => setEditOpen(true)}
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 mb-4"
          >
            Edit Task
          </button>   {/* ← ADDED */}

          {/* Delete Button */}
          <button
            onClick={() => setDeleteOpen(true)}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 mb-4 ml-3"
          >
            Delete Task
          </button>   {/* ← ADDED */}

          <p className="text-slate-700">{task.description}</p>

          {/* Timeline */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Timeline</h2>
            <TaskTimeline timeline={timeline} />
          </div>

          {/* Comments */}
          <TaskComments comments={comments} onAdd={addComment} />
        </div>

        {/* Meta Panel */}
        <TaskMeta task={task} onUpdate={updateTask} />
      </div>

      {/* Edit Panel */}
      <EditTaskPanel
        open={editOpen}
        onClose={() => setEditOpen(false)}
        task={task}
        onUpdated={(updated) => setTask(updated)}
      />   {/* ← ADDED */}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteOpen}
        title="Delete Task"
        message="Are you sure you want to delete this task? This action cannot be undone."
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => {
          api.delete(`/tasks/${task.id}`).then(() => {
            navigate("/tasks");
          });
        }}
      />   {/* ← ADDED */}
    </MainLayout>
  );
}