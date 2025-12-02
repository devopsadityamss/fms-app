import React, { useState } from "react";

export default function TaskComments({ comments, onAdd }) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim()) return;
    onAdd(text);
    setText("");
  };

  return (
    <div className="bg-white p-4 rounded shadow">
      <h3 className="font-semibold text-lg mb-3">Comments</h3>

      {/* Comment Input */}
      <div className="mb-4">
        <textarea
          className="w-full p-2 border rounded"
          rows={3}
          placeholder="Add a comment..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        ></textarea>
        <button
          onClick={submit}
          className="mt-2 bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Add Comment
        </button>
      </div>

      {/* Comment List */}
      <div className="space-y-4">
        {comments.map((c, index) => (
          <div key={index} className="border-b pb-2">
            <p className="text-slate-800">{c.text}</p>
            <p className="text-xs text-slate-500 mt-1">
              {c.author || "User"} — {new Date().toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
