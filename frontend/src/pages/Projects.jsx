import React, { useEffect, useState } from "react";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import ProjectCard from "../components/ProjectCard";
import CreateProjectPanel from "../components/CreateProjectPanel";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);

  // Fetch Projects
  const loadProjects = () => {
    api
      .get("/projects")
      .then((res) => setProjects(res.data))
      .catch(() => {});
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <MainLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>

        <button
          onClick={() => setCreateOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          + New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <p className="text-slate-600">No projects found.</p>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {/* Slide-In Panel */}
      <CreateProjectPanel
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => loadProjects()}
      />
    </MainLayout>
  );
}
