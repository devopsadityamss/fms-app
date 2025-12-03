import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import MainLayout from "../layout/MainLayout";
import { api } from "../services/api";
import { useUser } from "../context/UserContext";

export default function TaskDetail() {
  const { id } = useParams();
  const { token } = useUser();

  const [task, setTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [attachments, setAttachments] = useState([]);

  useEffect(() => {
    if (!token) return;

    api.get(`/tasks/${id}`, token)
      .then((res) => setTask(res.data))
      .catch((err) => console.error("Failed to load task", err));

    api.get(`/comments/task/${id}`, token)
      .then((res) => setComments(res.data))
      .catch((err) => console.error("Failed to load comments", err));

    // api.get(`/timeline/task/${id}`, token)
    //   .then((res) => setTimeline(res.data))
    //   .catch((err) => console.error("Failed to load timeline", err));

    // api.get(`/attachments/task/${id}`, token)
    //   .then((res) => setAttachments(res.data))
    //   .catch((err) => console.error("Failed to load attachments", err));

  }, [token, id]);

  if (!task) {
    return (
      <MainLayout>
        <p className="p-4">Loading task details...</p>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="p-4 space-y-8">
        
        {/* --- Task Info --- */}
        <div className="bg-white p-6 shadow rounded">
          <h1 className="text-2xl font-bold">{task.title}</h1>
          <p className="text-gray-600 mt-2">{task.description}</p>

          <div className="mt-4 text-sm text-gray-500">
            <p>Status: {task.status}</p>
            <p>Priority: {task.priority ?? "-"}</p>
            <p>Due date: {task.due_date ? new Date(task.due_date).toLocaleString() : "-"}</p>
          </div>
        </div>

        {/* --- Comments --- */}
        <div className="bg-white p-6 shadow rounded">
          <h2 className="text-xl font-semibold mb-4">Comments</h2>

          {comments.map((c) => (
            <div key={c.id} className="border-b py-2">
              <p>{c.text}</p>
              <small className="text-gray-500">
                {new Date(c.created_at).toLocaleString()}
              </small>
            </div>
          ))}

          {comments.length === 0 && (
            <p className="text-gray-400 italic">No comments yet.</p>
          )}
        </div>

        {/* --- Timeline --- */}
        <div className="bg-white p-6 shadow rounded">
          <h2 className="text-xl font-semibold mb-4">Timeline</h2>

          {timeline.map((t) => (
            <div key={t.id} className="border-b py-2">
              <p className="font-medium">{t.title}</p>
              <p className="text-gray-500 text-sm">{t.description}</p>
            </div>
          ))}

          {timeline.length === 0 && (
            <p className="text-gray-400 italic">No timeline events.</p>
          )}
        </div>

        {/* --- Attachments --- */}
        <div className="bg-white p-6 shadow rounded">
          <h2 className="text-xl font-semibold mb-4">Attachments</h2>

          {attachments.map((file) => (
            <a
              key={file.id}
              href={file.path}
              target="_blank"
              className="block py-2 text-blue-600 underline"
            >
              {file.name}
            </a>
          ))}

          {attachments.length === 0 && (
            <p className="text-gray-400 italic">No attachments.</p>
          )}
        </div>

      </div>
    </MainLayout>
  );
}
