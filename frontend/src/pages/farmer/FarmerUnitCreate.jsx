// frontend/src/pages/farmer/FarmerUnitCreate.jsx

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUser } from "../../context/UserContext";
import { farmerApi } from "../../api/farmer";

export default function FarmerUnitCreate() {
  const navigate = useNavigate();
  const { supabaseUser } = useUser();

  const [form, setForm] = useState({
    name: "",
    practice_type: "",
    category: "",
    meta: "{}",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleCreate = async () => {
    if (!supabaseUser?.id) {
      alert("User not logged in.");
      return;
    }

    if (!form.name || !form.practice_type) {
      alert("Name and Practice Type are required.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        user_id: supabaseUser.id,
        name: form.name,
        practice_type: form.practice_type,
        category: form.category || null,
        metadata: form.meta || "{}", // backend expects metadata JSON string
      };

      await farmerApi.createProductionUnit(payload);

      navigate("/farmer/dashboard");
    } catch (err) {
      console.error("Create unit failed:", err);
      alert("Failed to create unit");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-semibold">Create Production Unit</h1>

      <div className="bg-white shadow rounded-xl p-6 space-y-6">

        {/* NAME */}
        <div>
          <label className="block font-medium mb-1">Unit Name *</label>
          <input
            type="text"
            name="name"
            value={form.name}
            onChange={handleChange}
            className="w-full border rounded-lg p-2"
            placeholder="E.g., Tomato - Field 3"
          />
        </div>

        {/* PRACTICE TYPE */}
        <div>
          <label className="block font-medium mb-1">Practice Type *</label>
          <select
            name="practice_type"
            value={form.practice_type}
            onChange={handleChange}
            className="w-full border rounded-lg p-2"
          >
            <option value="">Select Practice</option>
            <option value="organic">Organic</option>
            <option value="natural">Natural</option>
            <option value="hydroponic">Hydroponic</option>
            <option value="traditional">Traditional</option>
          </select>
        </div>

        {/* CATEGORY */}
        <div>
          <label className="block font-medium mb-1">Category</label>
          <input
            type="text"
            name="category"
            value={form.category}
            onChange={handleChange}
            className="w-full border rounded-lg p-2"
            placeholder="Vegetables, Fruits, Flowers..."
          />
        </div>

        {/* OPTIONAL METADATA JSON */}
        <div>
          <label className="block font-medium mb-1">Metadata (JSON)</label>
          <textarea
            name="meta"
            value={form.meta}
            onChange={handleChange}
            className="w-full border rounded-lg p-2 h-32 font-mono"
            placeholder='{"soil_type": "loamy", "area": "1 acre"}'
          />
        </div>

        <button
          disabled={loading}
          className={`px-4 py-2 text-white rounded-lg shadow ${
            loading ? "bg-gray-400" : "bg-indigo-600 hover:bg-indigo-700"
          }`}
          onClick={handleCreate}
        >
          {loading ? "Creating..." : "Create Unit"}
        </button>
      </div>
    </div>
  );
}
