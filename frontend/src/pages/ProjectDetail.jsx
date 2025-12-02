import React, { useEffect, useState } from "react";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { useParams, useNavigate, Link } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    api.get(`/projects/${id}`).then((res) => setProject(res.data));
    api.get("/tasks", { params: { project_id: id } }).then((res) => setTasks(res.data));
  }, [id]);

  if (!project) return (
    <MainLayout>
      <p>Loading...</p>
    </MainLayout>
  );

  return (
    <MainLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">{project.name}</h1>

        <div className="flex gap-3">
          <Link
            to={`/tasks?project_id=${id}`}
            className="bg-indigo-600 text-white px-4 py-2 rounded"
          >
            View Tasks
          </Link>

          <button
            onClick={() => setDeleteOpen(true)}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Delete Project
          </button>
        </div>
      </div>

      <p className="text-slate-600 mb-6">{project.description}</p>

      <h2 className="text-xl font-semibold mb-2">Recent Tasks</h2>

      <div className="space-y-3">
        {tasks.map((t) => (
          <Link
            key={t.id}
            to={`/tasks/${t.id}`}
            className="block bg-white p-4 rounded shadow hover:shadow-md"
          >
            <h3 className="font-semibold">{t.title}</h3>
            <p className="text-sm text-slate-600">{t.status}</p>
          </Link>
        ))}
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Delete Project"
        message="Deleting this project will remove all tasks linked to it. This action cannot be undone."
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => {
          api.delete(`/projects/${id}`).then(() => {
            navigate("/projects");
          });
        }}
      />
    </MainLayout>
  );
}
