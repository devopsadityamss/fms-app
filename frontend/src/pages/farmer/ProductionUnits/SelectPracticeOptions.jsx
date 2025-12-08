import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

// Hardcoded options for MVP — each will later come from backend
const OPTION_MAP = {
  cereals: [
    { id: "rice", name: "Rice", img: "https://images.unsplash.com/photo-1599058917212-d750089bc07a" },
    { id: "wheat", name: "Wheat", img: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6" },
    { id: "maize", name: "Maize", img: "https://images.unsplash.com/photo-1592928302113-de6c3f2879d5" }
  ],

  pulses: [
    { id: "chickpea", name: "Chickpea", img: "https://images.unsplash.com/photo-1518977676601-b53f82aba655" },
    { id: "moong", name: "Green Gram", img: "https://images.unsplash.com/photo-1562615762-16dfd1a67c09" }
  ],

  oilseeds: [
    { id: "groundnut", name: "Groundnut", img: "https://images.unsplash.com/photo-1589314733670-98f9d34ef8b1" },
    { id: "sunflower", name: "Sunflower", img: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6" }
  ],

  millets: [
    { id: "ragi", name: "Ragi", img: "https://images.unsplash.com/photo-1591858353254-86b0d07f2599" },
    { id: "jowar", name: "Jowar", img: "https://images.unsplash.com/photo-1486887396153-fa416526c108" }
  ],

  cow: [
    { id: "hf", name: "HF Cow", img: "https://images.unsplash.com/photo-1517849845537-4d257902454a" },
    { id: "jersey", name: "Jersey Cow", img: "https://images.unsplash.com/photo-1522276498395-f4f68f7f8452" }
  ],

  buffalo: [
    { id: "murrah", name: "Murrah", img: "https://images.unsplash.com/photo-1588167056545-190d51189b9b" }
  ],

  freshwater: [
    { id: "rohu", name: "Rohu", img: "https://images.unsplash.com/photo-1523861751938-7f78b6a18e83" },
    { id: "catla", name: "Catla", img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4" },
    { id: "tilapia", name: "Tilapia", img: "https://images.unsplash.com/photo-1618828664709-c30a7985b1b3" }
  ]
};

export default function SelectPracticeOptions() {
  const { practiceId, categoryId } = useParams();
  const navigate = useNavigate();

  const options = OPTION_MAP[categoryId] || [];

  const [selectedOptions, setSelectedOptions] = useState([]);
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customName, setCustomName] = useState("");

  const toggleSelection = (id) => {
    setSelectedOptions((prev) =>
      prev.includes(id) ? prev.filter((o) => o !== id) : [...prev, id]
    );
  };

  const handleNext = () => {
    if (selectedOptions.length === 0) {
      alert("Please select at least one option.");
      return;
    }

    navigate(`/production/unit-details/${practiceId}/${categoryId}`, {
      state: { selectedOptions }
    });
  };

  const addCustomOption = () => {
    if (!customName.trim()) return;

    const customId = `custom_${customName.toLowerCase().replace(/\s+/g, "_")}`;

    setSelectedOptions((prev) => [...prev, customId]);

    OPTION_MAP[categoryId] = [
      ...(OPTION_MAP[categoryId] || []),
      {
        id: customId,
        name: customName,
        img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4" // placeholder image
      }
    ];

    setCustomName("");
    setShowCustomModal(false);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Select {categoryId} Options</h1>

      <div className="grid md:grid-cols-3 gap-6">
        {options.map((opt) => (
          <div
            key={opt.id}
            onClick={() => toggleSelection(opt.id)}
            className={`cursor-pointer rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition ${
              selectedOptions.includes(opt.id)
                ? "ring-4 ring-green-500"
                : "hover:-translate-y-1"
            }`}
          >
            <div className="h-40 w-full">
              <img src={opt.img} alt={opt.name} className="w-full h-full object-cover" />
            </div>

            <div className="p-4">
              <h2 className="text-xl font-semibold">{opt.name}</h2>
            </div>
          </div>
        ))}

        {/* Custom Option Card */}
        <div
          onClick={() => setShowCustomModal(true)}
          className="cursor-pointer rounded-xl flex flex-col justify-center items-center bg-gray-100 hover:bg-gray-200 shadow p-6 text-center"
        >
          <span className="text-4xl mb-2">➕</span>
          <span className="font-semibold">Add Custom Option</span>
        </div>
      </div>

      {/* Next Button */}
      <div className="mt-6">
        <button
          onClick={handleNext}
          className="px-6 py-2 bg-green-600 text-white rounded shadow hover:bg-green-700"
        >
          Next →
        </button>
      </div>

      {/* Custom Modal */}
      {showCustomModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-xl shadow-lg w-80">
            <h2 className="text-xl font-semibold mb-4">Add Custom Option</h2>

            <input
              type="text"
              placeholder="Enter name"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              className="w-full border p-2 rounded mb-4"
            />

            <div className="flex justify-end gap-3">
              <button onClick={() => setShowCustomModal(false)}>Cancel</button>
              <button
                onClick={addCustomOption}
                className="px-4 py-1 bg-green-600 text-white rounded"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
