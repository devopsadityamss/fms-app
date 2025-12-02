import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { useUser } from "../context/UserContext";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useUser();

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .get("/projects/", token)
      .then((res) => {
        if (!mounted) return;
        setProjects(res.data || []);
      })
      .catch((err) => {
        console.error("Failed to load projects:", err);
        setProjects([]);
      })
      .finally(() => mounted && setLoading(false));
    return () => (mounted = false);
  }, [token]);

  return (
    <MainLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Link
          to="/"
          className="px-3 py-1 text-sm bg-indigo-600 text-white rounded"
        >
          Back
        </Link>
      </div>

      {loading ? (
        <div>Loading projects...</div>
      ) : projects.length === 0 ? (
        <div>No projects found.</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {projects.map((p) => (
            <div key={p.id} className="p-4 bg-white rounded shadow">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">{p.name}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {p.description || "No description"}
                  </p>
                </div>
                <div>
                  <Link
                    to={`/projects/${p.id}`}
                    className="text-indigo-600 hover:underline"
                  >
                    Open
                  </Link>
                </div>
              </div>
              <div className="text-xs text-gray-400 mt-3">
                Created: {p.created_at || "-"}
              </div>
            </div>
          ))}
        </div>
      )}
    </MainLayout>
  );
}
