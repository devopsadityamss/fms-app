import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { useUser } from "../context/UserContext";

export default function ProjectDetail() {
  const { id } = useParams();
  const { token } = useUser();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    setLoading(true);

    // fetch project
    api
      .get(`/projects/${id}`, token)
      .then((res) => mounted && setProject(res.data))
      .catch((err) => {
        console.error("Failed to fetch project:", err);
        mounted && setProject(null);
      });

    // fetch tasks for project
    api
      .get(`/tasks?project_id=${id}`, token)
      .then((res) => mounted && setTasks(res.data || []))
      .catch((err) => {
        console.error("Failed to fetch tasks:", err);
        mounted && setTasks([]);
      })
      .finally(() => mounted && setLoading(false));

    return () => (mounted = false);
  }, [id, token]);

  if (!id) return <MainLayout>Invalid project id</MainLayout>;

  return (
    <MainLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {project ? project.name : "Project"}
          </h1>
          <p className="text-sm text-gray-600">{project?.description}</p>
        </div>
        <Link
          to="/projects"
          className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200"
        >
          Back to projects
        </Link>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="p-4 bg-white rounded shadow">
              <h3 className="font-semibold mb-2">Overview</h3>
              <div className="text-sm text-gray-700">
                ID: {project?.id}
                <br />
                Created: {project?.created_at}
                <br />
                Updated: {project?.updated_at}
              </div>
            </div>

            <div className="p-4 bg-white rounded shadow">
              <h3 className="font-semibold mb-2">Tasks</h3>
              {tasks.length === 0 ? (
                <div className="text-sm text-gray-500">No tasks for this project</div>
              ) : (
                <ul>
                  {tasks.map((t) => (
                    <li key={t.id} className="py-2 border-b last:border-b-0">
                      <Link to={`/tasks/${t.id}`} className="text-indigo-600">
                        {t.title}
                      </Link>
                      <div className="text-xs text-gray-500">{t.status}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </MainLayout>
  );
}
