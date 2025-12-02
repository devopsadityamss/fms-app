import React, { useEffect, useState } from "react";
import MainLayout from "../layout/MainLayout";
import { api } from "../api/client";
import { useUser } from "../context/UserContext";   // <-- correct import
import { TaskStatusPie, TasksByProjectBar } from "../components/TaskCharts";

export default function Dashboard() {
  const { token } = useUser();
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    if (!token) return;

    api.get("/projects/", token)
      .then((res) => setProjects(res.data))
      .catch(() => {});

    api.get("/tasks/", token)
      .then((res) => setTasks(res.data))
      .catch(() => {});
  }, [token]);

  return (
    <MainLayout>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="p-6 bg-white rounded shadow">
          <h3 className="font-semibold text-lg">Projects</h3>
          <div className="text-4xl mt-3">{projects.length}</div>
        </div>

        <div className="p-6 bg-white rounded shadow">
          <h3 className="font-semibold text-lg">Tasks</h3>
          <div className="text-4xl mt-3">{tasks.length}</div>
        </div>

        <div className="p-6 bg-white rounded shadow">
          <h3 className="font-semibold text-lg">Completed</h3>
          <div className="text-4xl mt-3">
            {tasks.filter((t) => t.status === "completed").length}
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mt-6">
        <div className="bg-white p-4 rounded shadow">
          <h4 className="font-semibold mb-2">Task status</h4>
          <TaskStatusPie data={tasks} />
        </div>

        <div className="bg-white p-4 rounded shadow">
          <h4 className="font-semibold mb-2">Tasks by project</h4>
          <TasksByProjectBar projects={projects} tasks={tasks} />
        </div>
      </div>
    </MainLayout>
  );
}
