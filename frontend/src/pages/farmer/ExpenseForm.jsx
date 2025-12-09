// src/pages/farmer/ExpenseForm.jsx

import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";

export default function ExpenseForm() {
  const { unitId, logId } = useParams();
  const navigate = useNavigate();

  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [notes, setNotes] = useState("");
  const [incurredOn, setIncurredOn] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [saving, setSaving] = useState(false);

  /* --------------------------------------------------
     SUBMIT EXPENSE
  -------------------------------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (Number(amount) <= 0) {
      toast.error("Amount must be greater than 0.");
      return;
    }

    const toastId = toast.loading("Saving expense...");
    setSaving(true);

    try {
      await farmerApi.addExpense({
        operation_log_id: logId || null,
        production_unit_id: unitId,
        amount: Number(amount),
        category,
        notes,
        incurred_on: incurredOn,
      });

      toast.dismiss(toastId);
      toast.success("Expense added!");

      navigate(`/farmer/production/unit/${unitId}/log/${logId}`);
    } catch (err) {
      console.error("Error adding expense:", err);
      toast.dismiss(toastId);
      toast.error("Failed to add expense.");
    } finally {
      setSaving(false);
    }
  };

  /* --------------------------------------------------
     UI
  -------------------------------------------------- */
  return (
    <div className="p-6 max-w-xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Add Expense</h1>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${logId}`}
          className="text-blue-600 underline"
        >
          ← Back
        </Link>
      </div>

      {/* FORM CARD */}
      <div className="bg-white p-6 rounded shadow">
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Amount */}
          <div>
            <label className="block text-sm font-semibold mb-1">
              Amount (₹) *
            </label>
            <input
              type="number"
              step="0.01"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="150.00"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-semibold mb-1">
              Category
            </label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="Fertilizer, Labour, Transport..."
            />
          </div>

          {/* Incurred On */}
          <div>
            <label className="block text-sm font-semibold mb-1">
              Incurred On
            </label>
            <input
              type="date"
              required
              value={incurredOn}
              onChange={(e) => setIncurredOn(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-semibold mb-1">Notes</label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="Optional description..."
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={saving}
            className={`w-full py-2 rounded shadow text-white ${
              saving
                ? "bg-yellow-300 cursor-not-allowed"
                : "bg-yellow-500 hover:bg-yellow-600"
            }`}
          >
            {saving ? "Saving..." : "Add Expense"}
          </button>
        </form>
      </div>
    </div>
  );
}
