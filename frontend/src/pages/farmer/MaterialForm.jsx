// src/pages/farmer/MaterialForm.jsx

import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";

export default function MaterialForm() {
  const { unitId, logId } = useParams();
  const navigate = useNavigate();

  const [materialName, setMaterialName] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitValue, setUnitValue] = useState("");
  const [cost, setCost] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  /* -------------------------------------------
     SUBMIT MATERIAL USAGE
  ------------------------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!materialName.trim()) {
      toast.error("Material name is required.");
      return;
    }

    const toastId = toast.loading("Saving material usage...");
    setSaving(true);

    try {
      await farmerApi.addMaterialUsage({
        operation_log_id: logId,
        material_name: materialName,
        material_id: materialId || null,
        quantity: quantity ? Number(quantity) : null,
        unit: unitValue || null,
        cost: cost ? Number(cost) : null,
        extra: notes ? { notes } : null
      });

      toast.dismiss(toastId);
      toast.success("Material usage saved!");

      navigate(`/farmer/production/unit/${unitId}/log/${logId}`);
    } catch (err) {
      console.error("Error adding material usage:", err);
      toast.dismiss(toastId);
      toast.error("Failed to save material usage.");
    } finally {
      setSaving(false);
    }
  };

  /* -------------------------------------------
     UI
  ------------------------------------------- */
  return (
    <div className="p-6 max-w-xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Add Material Usage</h1>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${logId}`}
          className="text-blue-600 underline"
        >
          ← Back
        </Link>
      </div>

      {/* FORM CARD */}
      <div className="bg-white p-6 rounded shadow">
        <form className="space-y-4" onSubmit={handleSubmit}>

          {/* Material Name */}
          <div>
            <label className="block text-sm font-semibold mb-1">
              Material Name *
            </label>
            <input
              type="text"
              required
              value={materialName}
              onChange={(e) => setMaterialName(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="Urea, Pesticide A, Seeds..."
            />
          </div>

          {/* Material ID */}
          <div>
            <label className="block text-sm font-semibold mb-1">
              Material ID (Optional)
            </label>
            <input
              type="text"
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="SKU / Inventory Code"
            />
          </div>

          {/* Quantity + Unit */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-semibold mb-1">Quantity</label>
              <input
                type="number"
                step="0.1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full border rounded px-3 py-2"
                placeholder="5"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1">Unit</label>
              <input
                type="text"
                value={unitValue}
                onChange={(e) => setUnitValue(e.target.value)}
                className="w-full border rounded px-3 py-2"
                placeholder="kg, liters, bags"
              />
            </div>
          </div>

          {/* Cost */}
          <div>
            <label className="block text-sm font-semibold mb-1">Cost (₹)</label>
            <input
              type="number"
              step="0.1"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="150"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-semibold mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border rounded px-3 py-2"
              rows={3}
              placeholder="Optional description..."
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={saving}
            className={`w-full py-2 rounded shadow text-white ${
              saving
                ? "bg-blue-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {saving ? "Saving..." : "Save Material Usage"}
          </button>
        </form>
      </div>
    </div>
  );
}
