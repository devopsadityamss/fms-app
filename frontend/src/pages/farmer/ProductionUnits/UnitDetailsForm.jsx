// src/pages/farmer/ProductionUnits/UnitDetailsForm.jsx
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useUser } from "../../../context/UserContext";
import toast from "react-hot-toast";

export default function UnitDetailsForm() {
  const navigate = useNavigate();
  const { practiceId, categoryId } = useParams();
  const location = useLocation();
  const { supabaseUser } = useUser();

  // Restore options from navigation *or* localStorage
  const selectedOptions =
    location.state?.selectedOptions ||
    JSON.parse(localStorage.getItem("selected_options") || "[]");

  // Load saved metadata if returning later
  const savedMetadata =
    JSON.parse(localStorage.getItem("unit_metadata") || "null") || {};

  const [form, setForm] = useState({
    name: savedMetadata.name || "",
    area: savedMetadata.area || "",
    soil_type: savedMetadata.soil_type || "",
    irrigation: savedMetadata.irrigation || "",
    animals: savedMetadata.animals || "",
    shed_size: savedMetadata.shed_size || "",
    feeding: savedMetadata.feeding || "",
    pond_size: savedMetadata.pond_size || "",
    water_source: savedMetadata.water_source || "",
    stocking_density: savedMetadata.stocking_density || ""
  });

  const [loadingNext, setLoadingNext] = useState(false);

  // Persist metadata continuously
  useEffect(() => {
    localStorage.setItem("unit_metadata", JSON.stringify(form));
  }, [form]);

  const handleChange = (key, value) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  /** ------------------- FIELDS PER PRACTICE ------------------- **/

  const renderCropFields = () => (
    <>
      <InputField label="Production Unit Name" id="name" value={form.name} onChange={handleChange} />
      <InputField label="Field Area (acres)" id="area" value={form.area} onChange={handleChange} />
      <InputField label="Soil Type" id="soil_type" value={form.soil_type} onChange={handleChange} />
      <InputField label="Irrigation Method" id="irrigation" value={form.irrigation} onChange={handleChange} />
    </>
  );

  const renderDairyFields = () => (
    <>
      <InputField label="Production Unit Name" id="name" value={form.name} onChange={handleChange} />
      <InputField label="Number of Animals" id="animals" value={form.animals} onChange={handleChange} />
      <InputField label="Shed Size (sq ft)" id="shed_size" value={form.shed_size} onChange={handleChange} />
      <InputField label="Feeding Method" id="feeding" value={form.feeding} onChange={handleChange} />
    </>
  );

  const renderFisheriesFields = () => (
    <>
      <InputField label="Production Unit Name" id="name" value={form.name} onChange={handleChange} />
      <InputField label="Pond Size (sq ft)" id="pond_size" value={form.pond_size} onChange={handleChange} />
      <InputField label="Water Source" id="water_source" value={form.water_source} onChange={handleChange} />
      <InputField label="Stocking Density" id="stocking_density" value={form.stocking_density} onChange={handleChange} />
    </>
  );

  const renderFields = () => {
    switch (practiceId) {
      case "crop":
        return renderCropFields();
      case "dairy":
        return renderDairyFields();
      case "fisheries":
        return renderFisheriesFields();
      default:
        return (
          <>
            <InputField label="Production Unit Name" id="name" value={form.name} onChange={handleChange} />
            <p className="text-sm text-gray-600">No additional metadata required for this practice.</p>
          </>
        );
    }
  };

  /** ------------------- VALIDATION ------------------- **/

  useEffect(() => {
    if (!selectedOptions || selectedOptions.length === 0) {
      navigate(`/farmer/production/select-options/${practiceId}/${categoryId}`);
    }
  }, [selectedOptions, practiceId, categoryId, navigate]);

  const handleNext = async () => {
    if (!supabaseUser?.id) {
      toast.error("Please log in.");
      return;
    }
    if (!form.name.trim()) {
      toast.error("Production unit name is required.");
      return;
    }
    if (!selectedOptions.length) {
      toast.error("Please select at least one practice option.");
      return;
    }

    let t;
    try {
      setLoadingNext(true);
      t = toast.loading("Saving details...");

      const metadata = { ...form };

      // Save metadata
      localStorage.setItem("unit_metadata", JSON.stringify(metadata));

      toast.dismiss(t);
      toast.success("Details saved!");

      navigate(`/farmer/production/stages`, {
        state: {
          practiceId,
          categoryId,
          selectedOptions,
          metadata
        }
      });

    } catch (err) {
      toast.dismiss(t);
      toast.error("Failed to save details.");
      console.error("Unit details error:", err);
    } finally {
      setLoadingNext(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <button
          className="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>
        <h1 className="text-3xl font-bold">Production Unit Details</h1>
      </div>

      {/* Selected Options */}
      <p className="mb-4 text-gray-600">
        <strong>Selected Options:</strong> {selectedOptions.join(", ") || "-"}
      </p>

      {/* Form Container */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        {renderFields()}
      </div>

      {/* Footer */}
      <div className="mt-6 flex gap-3">
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-gray-200 rounded">
          Back
        </button>

        <button
          onClick={handleNext}
          disabled={loadingNext}
          className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
        >
          {loadingNext ? "Saving..." : "Next: Review Stages →"}
        </button>
      </div>
    </div>
  );
}

/* ---------- Reusable Input Component ---------- */
function InputField({ label, id, value, onChange }) {
  return (
    <div className="mb-4">
      <label className="block mb-1 font-medium">{label}</label>
      <input
        type="text"
        value={value || ""}
        onChange={(e) => onChange(id, e.target.value)}
        className="w-full border p-2 rounded"
      />
    </div>
  );
}
