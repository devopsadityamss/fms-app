import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";

// Hardcoded options for MVP — backend later
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

  const baseOptions = OPTION_MAP[categoryId] || [];
  const [options, setOptions] = useState(baseOptions);

  const [selectedOptions, setSelectedOptions] = useState(
    JSON.parse(localStorage.getItem("selected_options") || "[]")
  );

  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customName, setCustomName] = useState("");

  const [loadingNext, setLoadingNext] = useState(false);
  const [loadingCustom, setLoadingCustom] = useState(false);

  // Redirect if invalid category
  useEffect(() => {
    if (!OPTION_MAP[categoryId]) {
      navigate(`/farmer/production/select-category/${practiceId}`);
    }
  }, [categoryId, navigate, practiceId]);

  // Load any previously saved custom options for this category
  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem("custom_options") || "{}");
    if (stored[categoryId]) {
      setOptions([...baseOptions, ...stored[categoryId]]);
    }
  }, [categoryId]);

  const toggleSelection = (id) => {
    setSelectedOptions((prev) =>
      prev.includes(id)
        ? prev.filter((o) => o !== id)
        : [...prev, id]
    );
  };

  const handleNext = async () => {
    if (selectedOptions.length === 0) {
      toast.error("Please select at least one option.");
      return;
    }

    let t;
    try {
      setLoadingNext(true);
      t = toast.loading("Saving selection...");

      localStorage.setItem("selected_options", JSON.stringify(selectedOptions));

      toast.dismiss(t);
      toast.success("Options selected!");

      navigate(`/farmer/production/unit-details/${practiceId}/${categoryId}`, {
        state: { selectedOptions }
      });

    } catch (err) {
      toast.dismiss(t);
      toast.error("Could not proceed.");
      console.error("Next step error:", err);
    } finally {
      setLoadingNext(false);
    }
  };

  const addCustomOption = async () => {
    if (!customName.trim()) {
      toast.error("Enter a valid name.");
      return;
    }

    const customId = `custom_${customName.toLowerCase().replace(/\s+/g, "_")}`;

    // Prevent duplicates
    if (options.find((o) => o.id === customId)) {
      toast.error("Option already exists.");
      return;
    }

    let t;
    try {
      setLoadingCustom(true);
      t = toast.loading("Adding custom option...");

      const newOption = {
        id: customId,
        name: customName.trim(),
        img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4"
      };

      // Add visually
      setOptions((prev) => [...prev, newOption]);
      setSelectedOptions((prev) => [...prev, customId]);

      // Save in localStorage
      const stored = JSON.parse(localStorage.getItem("custom_options") || "{}");
      stored[categoryId] = [...(stored[categoryId] || []), newOption];
      localStorage.setItem("custom_options", JSON.stringify(stored));

      setCustomName("");
      setShowCustomModal(false);

      toast.dismiss(t);
      toast.success("Custom option added!");

    } catch (err) {
      toast.dismiss(t);
      toast.error("Failed to add option.");
      console.error("Custom option error:", err);
    } finally {
      setLoadingCustom(false);
    }
  };

  return (
    <div className="p-8">

      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>

        <h1 className="text-3xl font-bold">Select Options</h1>
      </div>

      {/* Options Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {options.map((opt) => (
          <div
            key={opt.id}
            onClick={() => toggleSelection(opt.id)}
            className={`cursor-pointer rounded-xl overflow-hidden shadow-lg transition ${
              selectedOptions.includes(opt.id)
                ? "ring-4 ring-green-500"
                : "hover:shadow-2xl hover:-translate-y-1"
            } bg-white`}
          >
            <div className="h-40 w-full overflow-hidden">
              <img
                src={opt.img}
                alt={opt.name}
                className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
              />
            </div>

            <div className="p-4">
              <h2 className="text-xl font-semibold">{opt.name}</h2>
            </div>
          </div>
        ))}

        {/* Add Custom Option */}
        <div
          onClick={() => setShowCustomModal(true)}
          className="cursor-pointer rounded-xl flex flex-col justify-center items-center bg-gray-100 hover:bg-gray-200 shadow p-6 text-center"
        >
          <span className="text-4xl mb-2">➕</span>
          <span className="font-semibold">Add Custom Option</span>
        </div>
      </div>

      {/* Next button */}
      <div className="mt-6">
        <button
          onClick={handleNext}
          disabled={loadingNext}
          className="px-6 py-2 bg-green-600 text-white rounded shadow hover:bg-green-700 disabled:bg-gray-400"
        >
          {loadingNext ? "Saving..." : "Next →"}
        </button>
      </div>

      {/* Custom Option Modal */}
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
              <button
                onClick={() => !loadingCustom && setShowCustomModal(false)}
                className="px-4 py-1"
              >
                Cancel
              </button>

              <button
                disabled={loadingCustom}
                onClick={addCustomOption}
                className="px-4 py-1 bg-green-600 text-white rounded disabled:bg-gray-400"
              >
                {loadingCustom ? "Adding..." : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
