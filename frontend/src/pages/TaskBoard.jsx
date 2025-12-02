import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../layout/MainLayout";
import { api } from "../services/api";
import { useUser } from "../context/UserContext";

export default function TaskBoard() {
  const { token } = useUser();
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    if (!token) return;

    api.get("/tasks", token)
      .then((res) => setTasks(res.data))
      .catch((err) => console.error("Failed to load tasks:", err));
  }, [token]);

  const pending = tasks.filter((t) => t.status === "pending");
  const inProgress = tasks.filter((t) => t.status === "in_progress");
  const completed = tasks.filter((t) => t.status === "completed");

  const Column = ({ title, items }) => (
    <div className="w-full p-4 bg-white shadow rounded">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>

      {items.map((task) => (
        <Link
          to={`/tasks/${task.id}`}
          key={task.id}
          className="block p-3 border rounded mb-3 hover:bg-gray-100"
        >
          <h3 className="font-medium">{task.title}</h3>
          <p className="text-sm text-gray-500">
            Project: {task.project_id} • Priority: {task.priority ?? "-"}
          </p>
        </Link>
      ))}

      {items.length === 0 && (
        <p className="text-gray-400 text-sm italic">No tasks</p>
      )}
    </div>
  );

  return (
    <MainLayout>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4">
        <Column title="Pending" items={pending} />
        <Column title="In Progress" items={inProgress} />
        <Column title="Completed" items={completed} />
      </div>
    </MainLayout>
  );
}
