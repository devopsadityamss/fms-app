// src/pages/farmer/ProductionUnits/StageTemplateEditor.jsx
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../../../services/api";
import { v4 as uuidv4 } from "uuid";

/**
 * FRONTEND TEMPLATE LIBRARY (MVP hardcoded)
 * Each option maps to a list of stages (stages contain default tasks).
 * Later these will be moved to backend.
 */
const TEMPLATE_LIBRARY = {
  rice: [
    { title: "Soil Test", tasks: ["Collect sample", "Send sample to lab", "Apply recommendation"] },
    { title: "Land Preparation", tasks: ["Plough", "Level land", "Drainage checks"] },
    { title: "Sowing/Transplanting", tasks: ["Prepare nursery", "Transplant seedlings"] },
    { title: "Irrigation", tasks: ["Set schedule", "Irrigate as per schedule"] },
    { title: "Fertilizer & Spray", tasks: ["Fertilizer application", "Pesticide spray"] },
    { title: "Harvest", tasks: ["Harvest crop", "Threshing"] },
    { title: "Post-Harvest", tasks: ["Drying", "Storage"] }
  ],
  tomato: [
    { title: "Nursery", tasks: ["Prepare nursery beds", "Sow seeds"] },
    { title: "Transplanting", tasks: ["Transplant seedlings"] },
    { title: "Irrigation", tasks: ["Drip setup", "Irrigation schedule"] },
    { title: "Fertilizer & Spray", tasks: ["Fertigation", "Pest control"] },
    { title: "Harvest", tasks: ["Harvest ripe fruits", "Pack & dispatch"] }
  ],
  marigold: [
    { title: "Land Preparation", tasks: ["Prepare bed", "Fertilize"] },
    { title: "Direct Sowing", tasks: ["Sow seeds", "Initial irrigation"] },
    { title: "Pinching & Maintenance", tasks: ["Pinch plants", "Weed control"] },
    { title: "Harvest", tasks: ["Cut flowers", "Bundle"] }
  ],
  hf: [
    { title: "Shed Maintenance", tasks: ["Clean shed", "Inspect bedding"] },
    { title: "Feeding Routine", tasks: ["Prepare feed", "Feed cows"] },
    { title: "Milking", tasks: ["Milking twice daily", "Store milk"] },
    { title: "Health Check", tasks: ["Veterinary check-up", "Vaccination schedule"] }
  ],
  rohu: [
    { title: "Pond Preparation", tasks: ["Drain/clean pond", "Check water parameters"] },
    { title: "Stocking", tasks: ["Purchase fingerlings", "Stock pond"] },
    { title: "Feeding", tasks: ["Daily feed", "Record feed usage"] },
    { title: "Harvest", tasks: ["Netting", "Sorting"] }
  ]
};

/**
 * Merge algorithm:
 * - Collect stage titles from all templates in order they appear
 * - If a stage title already exists (case-insensitive), merge tasks (unique)
 * - Keep order based on first occurrence
 */
function mergeTemplates(optionIds) {
  const merged = [];
  const seen = new Map();

  optionIds.forEach((optId) => {
    const tpl = TEMPLATE_LIBRARY[optId] || [];
    tpl.forEach((stage) => {
      const key = stage.title.trim().toLowerCase();
      if (!seen.has(key)) {
        const copy = {
          id: uuidv4(),
          title: stage.title,
          tasks: (stage.tasks || []).map((t) => ({ id: uuidv4(), title: t }))
        };
        merged.push(copy);
        seen.set(key, copy);
      } else {
        // merge tasks
        const existing = seen.get(key);
        (stage.tasks || []).forEach((t) => {
          if (!existing.tasks.find((et) => et.title === t)) {
            existing.tasks.push({ id: uuidv4(), title: t });
          }
        });
      }
    });
  });

  return merged;
}

export default function StageTemplateEditor() {
  const loc = useLocation();
  const navigate = useNavigate();
  const state = loc.state || {};
  const { practiceId, categoryId, selectedOptions = [], metadata = {} } = state;

  const [stages, setStages] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // merge templates for selected options
    const merged = mergeTemplates(selectedOptions);
    setStages(merged);
  }, [selectedOptions]);

  // UI helpers
  const addStage = () => {
    setStages((s) => [...s, { id: uuidv4(), title: "New Stage", tasks: [] }]);
  };

  const removeStage = (stageId) => {
    setStages((s) => s.filter((st) => st.id !== stageId));
  };

  const moveStage = (index, dir) => {
    setStages((prev) => {
      const arr = [...prev];
      const target = arr[index + dir];
      if (!target) return prev;
      arr[index + dir] = arr[index];
      arr[index] = target;
      return arr;
    });
  };

  const updateStageTitle = (id, title) => {
    setStages((prev) => prev.map((st) => (st.id === id ? { ...st, title } : st)));
  };

  // tasks
  const addTask = (stageId) => {
    setStages((prev) =>
      prev.map((st) =>
        st.id === stageId ? { ...st, tasks: [...st.tasks, { id: uuidv4(), title: "New task" }] } : st
      )
    );
  };

  const updateTaskTitle = (stageId, taskId, title) => {
    setStages((prev) =>
      prev.map((st) =>
        st.id === stageId ? { ...st, tasks: st.tasks.map((t) => (t.id === taskId ? { ...t, title } : t)) } : st
      )
    );
  };

  const removeTask = (stageId, taskId) => {
    setStages((prev) => prev.map((st) => (st.id === stageId ? { ...st, tasks: st.tasks.filter((t) => t.id !== taskId) } : st)));
  };

  // Final save — create Production Unit via API
  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        user_id: metadata.user_id || null, // backend will check auth — but we include if present
        practice_type: practiceId,
        category: categoryId,
        name: metadata.name,
        items: selectedOptions,
        metadata,
        stages: stages.map((s, idx) => ({
          title: s.title,
          order: idx + 1,
          tasks: s.tasks.map((t, j) => ({ title: t.title, order: j + 1 }))
        }))
      };

      const res = await api.post("/farmer/production-unit/create", payload);
      // res.data should include created unit id
      const unitId = res.data?.id;
      alert("Production unit created successfully");
      navigate(`/farmer/production/unit/${unitId}`, { replace: true });
    } catch (e) {
      console.error(e);
      alert("Failed to create production unit");
    } finally {
      setSaving(false);
    }
  };

  if (!selectedOptions || selectedOptions.length === 0) {
    return (
      <div className="p-8">
        <h2 className="text-xl font-semibold">No options selected</h2>
        <p>Please go back and select at least one crop/animal.</p>
        <button className="mt-4 px-4 py-2 bg-gray-200 rounded" onClick={() => navigate(-1)}>Back</button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Review & Edit Stages</h1>
      <p className="mb-4 text-gray-600">Production Unit: <strong>{metadata.name}</strong></p>

      <div className="mb-4">
        <button onClick={addStage} className="px-3 py-1 bg-blue-600 text-white rounded">Add Stage</button>
      </div>

      <div className="space-y-4">
        {stages.map((stage, idx) => (
          <div key={stage.id} className="bg-white p-4 rounded shadow">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-500">#{idx + 1}</div>
                <input
                  value={stage.title}
                  onChange={(e) => updateStageTitle(stage.id, e.target.value)}
                  className="text-lg font-semibold border-b px-2 py-1"
                />
                <div className="text-sm text-gray-400 ml-2">{stage.tasks.length} tasks</div>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={() => moveStage(idx, -1)} className="px-2 py-1 bg-gray-100 rounded">↑</button>
                <button onClick={() => moveStage(idx, 1)} className="px-2 py-1 bg-gray-100 rounded">↓</button>
                <button onClick={() => removeStage(stage.id)} className="px-2 py-1 bg-red-100 text-red-700 rounded">Delete</button>
              </div>
            </div>

            {/* Tasks */}
            <div className="mt-3 space-y-2">
              {stage.tasks.map((t) => (
                <div key={t.id} className="flex items-center gap-2">
                  <input
                    value={t.title}
                    onChange={(e) => updateTaskTitle(stage.id, t.id, e.target.value)}
                    className="flex-1 border p-2 rounded"
                  />
                  <button onClick={() => removeTask(stage.id, t.id)} className="px-2 py-1 bg-red-100 text-red-700 rounded">Remove</button>
                </div>
              ))}

              <div>
                <button onClick={() => addTask(stage.id)} className="mt-2 px-3 py-1 bg-green-600 text-white rounded">+ Add Task</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex gap-3">
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-gray-200 rounded">Back</button>
        <button onClick={handleSave} disabled={saving} className="px-6 py-2 bg-emerald-600 text-white rounded">
          {saving ? "Saving..." : "Save Production Unit"}
        </button>
      </div>
    </div>
  );
}
