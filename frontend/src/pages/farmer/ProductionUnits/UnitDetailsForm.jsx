// src/pages/farmer/ProductionUnits/UnitDetailsForm.jsx
import React, { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useUser } from "../../../context/UserContext";

export default function UnitDetailsForm() {
  const navigate = useNavigate();
  const { practiceId, categoryId } = useParams();
  const location = useLocation();
  const { supabaseUser } = useUser();

  const selectedOptions = location.state?.selectedOptions || [];

  const [form, setForm] = useState({
    name: "",
    area: "",
    soil_type: "",
    irrigation: "",
    animals: "",
    shed_size: "",
    feeding: "",
    pond_size: "",
    water_source: "",
    stocking_density: ""
  });

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  // Minimal fields depending on practice
  const renderCropFields = () => (
    <>
      <InputField label="Production Unit Name" id="name" value={form.name} onChange={handleChange} />
      <InputField label="Field Area (in acres)" id="area" value={form.area} onChange={handleChange} />
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

  const handleNext = () => {
    if (!supabaseUser?.id) {
      alert("Please log in.");
      return;
    }
    if (!form.name || form.name.trim().length === 0) {
      alert("Please provide a name for the production unit.");
      return;
    }

    // Navigate to Stage Template Editor with the collected data
    navigate(`/farmer/production/stages`, {
      state: {
        practiceId,
        categoryId,
        selectedOptions,
        metadata: form
      }
    });
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Production Unit Details</h1>

      <p className="mb-4 text-gray-600">Selected Items: <strong>{selectedOptions.join(", ") || "-"}</strong></p>

      <div className="bg-white p-6 rounded-lg shadow-md">{renderFields()}</div>

      <div className="mt-6 flex gap-3">
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-gray-200 rounded">Back</button>
        <button onClick={handleNext} className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700">
          Next: Review Stages
        </button>
      </div>
    </div>
  );
}

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
