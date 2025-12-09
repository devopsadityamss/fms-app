// src/pages/farmer/OperationLogDetail.jsx

import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { farmerApi } from "../../api/farmer";
import toast from "react-hot-toast";

export default function OperationLogDetail() {
  const { unitId, logId } = useParams();
  const navigate = useNavigate();

  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadLog = async () => {
    let toastId;
    try {
      toastId = toast.loading("Loading log details...");
      setLoading(true);

      const data = await farmerApi.getOperationLog(logId);
      setLog(data || null);

      toast.dismiss(toastId);
      toast.success("Log loaded!");
    } catch (err) {
      console.error("Error loading log detail:", err);
      toast.dismiss();
      toast.error("Failed to load log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLog();
  }, [logId]);

  if (loading) return <div className="p-6">Loading log details...</div>;
  if (!log) return <div className="p-6">Log not found</div>;

  const displayDate = log.performed_on
    ? new Date(log.performed_on).toLocaleDateString()
    : "-";

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Activity Details</h1>

        <button
          onClick={() => navigate(-1)}
          className="text-blue-600 underline"
        >
          ← Back
        </button>
      </div>

      {/* MAIN CARD */}
      <div className="bg-white shadow rounded p-4 space-y-3">

        <div className="text-lg font-semibold">{displayDate}</div>

        <div className="text-gray-700">
          <strong>Status:</strong> {log.status || "N/A"}
        </div>

        {/* Stage & Task */}
        <div className="text-gray-700">
          <strong>Stage:</strong> {log.stage?.name || "N/A"} <br />
          <strong>Task:</strong> {log.task_template?.name || "N/A"}
        </div>

        {/* Quantity */}
        {(log.quantity || log.unit) && (
          <div className="text-gray-700">
            <strong>Quantity:</strong> {log.quantity || "?"} {log.unit || ""}
          </div>
        )}

        {/* Notes */}
        {log.notes && (
          <div className="bg-gray-100 text-gray-700 p-3 rounded text-sm">
            {log.notes}
          </div>
        )}
      </div>

      {/* ACTION BUTTONS — FIXED ROUTES */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ActionButton
          to={`/farmer/production/unit/${unitId}/log/material/${logId}`}
          label="Add Material"
          icon="➕"
          color="blue"
        />
        <ActionButton
          to={`/farmer/production/unit/${unitId}/log/labour/${logId}`}
          label="Add Labour"
          icon="👷"
          color="purple"
        />
        <ActionButton
          to={`/farmer/production/unit/${unitId}/expense`}
          label="Add Expense"
          icon="💰"
          color="yellow"
        />
        <ActionButton
          to={`/farmer/production/unit/${unitId}/log/media/${logId}`}
          label="Add Media"
          icon="📷"
          color="gray"
        />
      </div>

      {/* MATERIALS */}
      <Section title="Materials Used">
        {!log.materials?.length ? (
          <Empty text="No materials recorded." />
        ) : (
          <List
            items={log.materials}
            render={(m) => (
              <div>
                <strong>{m.material_name}</strong> — {m.quantity || "?"}{" "}
                {m.unit || ""}
                {m.cost && (
                  <span className="text-sm text-gray-500"> (₹{m.cost})</span>
                )}
              </div>
            )}
          />
        )}
      </Section>

      {/* LABOUR */}
      <Section title="Labour Usage">
        {!log.labour?.length ? (
          <Empty text="No labour recorded." />
        ) : (
          <List
            items={log.labour}
            render={(l) => (
              <div>
                👷 {l.worker_name || "Worker"} — {l.hours || "?"} hrs
                {l.labour_cost && (
                  <span className="text-sm text-gray-500">
                    {" "}
                    (₹{l.labour_cost})
                  </span>
                )}
              </div>
            )}
          />
        )}
      </Section>

      {/* EXPENSES */}
      <Section title="Expenses">
        {!log.expenses?.length ? (
          <Empty text="No expenses recorded." />
        ) : (
          <List
            items={log.expenses}
            render={(e) => (
              <div>
                💰 ₹{e.amount} — {e.category || "Uncategorized"}
                {e.notes && (
                  <div className="text-sm text-gray-600">{e.notes}</div>
                )}
              </div>
            )}
          />
        )}
      </Section>

      {/* MEDIA */}
      <Section title="Media">
        {!log.media?.length ? (
          <Empty text="No media uploaded." />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {log.media.map((m) => (
              <div key={m.id} className="bg-gray-100 p-2 rounded">
                <img
                  src={m.file_url}
                  alt={m.caption || "media"}
                  className="w-full h-32 object-cover rounded"
                />
                {m.caption && (
                  <div className="text-xs text-gray-600 mt-1">
                    {m.caption}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

/* -----------------------
   REUSABLE COMPONENTS
------------------------- */

function ActionButton({ to, label, icon, color }) {
  const colors = {
    blue: "bg-blue-600 hover:bg-blue-700",
    purple: "bg-purple-600 hover:bg-purple-700",
    yellow: "bg-yellow-500 hover:bg-yellow-600",
    gray: "bg-gray-700 hover:bg-gray-800"
  };

  return (
    <Link
      to={to}
      className={`${colors[color]} text-white px-3 py-2 rounded text-center`}
    >
      {icon} {label}
    </Link>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">{title}</h2>
      <div className="bg-white shadow rounded p-3">{children}</div>
    </div>
  );
}

function Empty({ text }) {
  return <div className="text-gray-500 text-sm">{text}</div>;
}

function List({ items, render }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.id}
          className="border-b pb-2 last:border-none last:pb-0"
        >
          {render(item)}
        </div>
      ))}
    </div>
  );
}
