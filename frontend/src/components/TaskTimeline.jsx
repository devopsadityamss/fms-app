import React from "react";

export default function TaskTimeline({ timeline }) {
  if (!timeline?.length)
    return <p className="text-slate-500 text-sm">No timeline activity.</p>;

  return (
    <div className="space-y-4">
      {timeline.map((item, index) => (
        <div key={index} className="flex items-start gap-3">
          <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2"></div>

          <div>
            <p className="font-medium">{item.title}</p>
            <p className="text-sm text-slate-600">{item.description}</p>
            <p className="text-xs text-slate-400 mt-1">
              {new Date(item.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
