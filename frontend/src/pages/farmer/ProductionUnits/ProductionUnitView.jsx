// src/pages/farmer/ProductionUnits/ProductionUnitView.jsx
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../../../services/api";

export default function ProductionUnitView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [unit, setUnit] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get(`/farmer/production-unit/${id}`)
      .then((res) => setUnit(res.data))
      .catch((err) => {
        console.error(err);
        alert("Failed to load production unit");
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8">Loading...</div>;
  if (!unit) return <div className="p-8">Not found</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{unit.name}</h1>
          <div className="text-sm text-gray-600">{unit.practice_type} • {unit.category}</div>
        </div>
        <button className="px-3 py-1 bg-gray-200 rounded" onClick={() => navigate(-1)}>Back</button>
      </div>

      <div className="space-y-4">
        {unit.stages.map((s, idx) => (
          <div key={s.id} className="bg-white p-4 rounded shadow">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-500">Stage {idx + 1}</div>
                <div className="text-lg font-semibold">{s.title}</div>
              </div>
              <div className="text-sm text-gray-400">Tasks: {s.tasks.length}</div>
            </div>

            <ul className="mt-3 ml-4 list-disc text-sm text-gray-700">
              {s.tasks.map((t) => (
                <li key={t.id}>{t.title} {t.completed ? <span className="text-green-600 ml-2">(Done)</span> : null}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}