// src/pages/farmer/ProductionUnits/StageTemplateEditor.jsx
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../../services/api";            // FIXED PATH
import { useUser } from "../../../context/UserContext"; // REQUIRED FOR user_id
import { v4 as uuidv4 } from "uuid";

/* ---------- TEMPLATE_LIBRARY stays unchanged ---------- */
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

/* ---------- Merge Logic stays unchanged ---------- */
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

/* ============================================================
   COMPONENT START
   ============================================================ */
export default function StageTemplateEditor() {
  const navigate = useNavigate();
  const loc = useLocation();
  const { supabaseUser } = useUser();        // REQUIRED FOR user_id

  const { practiceId, categoryId, selectedOptions = [], metadata = {} } =
    loc.state || {};

  const [stages, setStages] = useState([]);
  const [saving, setSaving] = useState(false);

  // Merge templates into editable stage list
  useEffect(() => {
    const merged = mergeTemplates(selectedOptions);
    setStages(merged);
  }, [selectedOptions]);

  /* -------------------- Stage & Task helpers --------------------- */

  const addStage = () => {
    setStages((s) => [...s, { id: uuidv4(), title: "New Stage", tasks: [] }]);
  };

  const removeStage = (stageId) => {
    setStages((s) => s.filter((st) => st.id !== stageId));
  };

  const moveStage = (index, dir) => {
    setStages((prev) => {
      const arr = [...prev];
      if (!arr[index + dir]) return prev;
      const temp = arr[index];
      arr[index] = arr[index + dir];
      arr[index + dir] = temp;
      return arr;
    });
  };

  const updateStageTitle = (id, title) => {
    setStages((prev) => prev.map((st) => (st.id === id ? { ...st, title } : st)));
  };

  const addTask = (stageId) => {
    setStages((prev) =>
      prev.map((st) =>
        st.id === stageId
          ? { ...st, tasks: [...st.tasks, { id: uuidv4(), title: "New task" }] }
          : st
      )
    );
  };

  const updateTaskTitle = (stageId, taskId, title) => {
    setStages((prev) =>
      prev.map((st) =>
        st.id === stageId
          ? {
              ...st,
              tasks: st.tasks.map((t) => (t.id === taskId ? { ...t, title } : t))
            }
          : st
      )
    );
  };

  const removeTask = (stageId, taskId) => {
    setStages((prev) =>
      prev.map((st) =>
        st.id === stageId
          ? { ...st, tasks: st.tasks.filter((t) => t.id !== taskId) }
          : st
      )
    );
  };

  /* -------------------- FINAL SAVE --------------------- */

  const handleSave = async () => {
    if (!supabaseUser?.id) {
      alert("Please login first.");
      return;
    }

    setSaving(true);

    try {
      const payload = {
        user_id: supabaseUser.id, // FIXED
        practice_type: practiceId,
        category: categoryId,
        name: metadata.name,
        items: selectedOptions,   // backend normalizes this
        meta: JSON.stringify(metadata), // FIXED: must be JSON string
        stages: stages.map((s, idx) => ({
          title: s.title,
          order: idx + 1,
          tasks: s.tasks.map((t, j) => ({
            title: t.title,
            order: j + 1
          }))
        }))
      };

      const res = await api.post("/farmer/production-unit/create", payload);
      const unitId = res?.data?.id;

      alert("Production Unit Created Successfully!");
      navigate(`/farmer/production/unit/${unitId}`, { replace: true });
    } catch (err) {
      console.error(err);
      alert("Failed to create production unit.");
    } finally {
      setSaving(false);
    }
  };

  /* -------------------- Render --------------------- */

  if (!selectedOptions.length) {
    return (
      <div className="p-8">
        <h2 className="text-xl font-semibold">No options selected</h2>
        <button onClick={() => navigate(-1)} className="mt-4 px-4 py-2 bg-gray-200 rounded">
          Back
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Review & Edit Stages</h1>
      <p className="mb-4 text-gray-600">Production Unit: <strong>{metadata.name}</strong></p>

      <button onClick={addStage} className="px-3 py-1 bg-blue-600 text-white rounded mb-4">
        Add Stage
      </button>

      <div className="space-y-4">
        {stages.map((stage, idx) => (
          <div key={stage.id} className="bg-white p-4 rounded shadow">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="text-gray-500">#{idx + 1}</div>
                <input
                  value={stage.title}
                  onChange={(e) => updateStageTitle(stage.id, e.target.value)}
                  className="text-lg border-b px-2"
                />
              </div>

              <div className="flex gap-2">
                <button onClick={() => moveStage(idx, -1)} className="px-2 py-1 bg-gray-100 rounded">Up</button>
                <button onClick={() => moveStage(idx, 1)} className="px-2 py-1 bg-gray-100 rounded">Down</button>
                <button
                  onClick={() => removeStage(stage.id)}
                  className="px-2 py-1 bg-red-100 text-red-600 rounded"
                >
                  Delete
                </button>
              </div>
            </div>

            {/* Tasks */}
            <div className="mt-3 space-y-2">
              {stage.tasks.map((task) => (
                <div key={task.id} className="flex gap-2 items-center">
                  <input
                    value={task.title}
                    onChange={(e) => updateTaskTitle(stage.id, task.id, e.target.value)}
                    className="flex-1 border p-2 rounded"
                  />
                  <button
                    onClick={() => removeTask(stage.id, task.id)}
                    className="px-2 py-1 bg-red-100 text-red-600 rounded"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button onClick={() => addTask(stage.id)} className="mt-2 px-3 py-1 bg-green-600 text-white rounded">
                + Add Task
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-6 flex gap-3">
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-gray-200 rounded">Back</button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-emerald-600 text-white rounded"
        >
          {saving ? "Saving..." : "Save Production Unit"}
        </button>
      </div>
    </div>
  );
}
