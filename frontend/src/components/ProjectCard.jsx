import React from "react";
import { Link } from "react-router-dom";

export default function ProjectCard({ project }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-all flex flex-col justify-between">
      <div>
        <h3 className="text-xl font-semibold text-slate-800">{project.name}</h3>

        {project.description && (
          <p className="text-sm text-slate-600 mt-2 line-clamp-3">
            {project.description}
          </p>
        )}
      </div>

      <Link
        to={`/tasks?project_id=${project.id}`}
        className="text-indigo-600 font-medium mt-4 hover:underline"
      >
        View Tasks →
      </Link>
    </div>
  );
}
