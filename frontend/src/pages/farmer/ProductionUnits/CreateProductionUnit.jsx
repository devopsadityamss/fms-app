import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

// Temporary hardcoded practices (MVP) — backend later
const PRACTICES = [
  {
    id: "crop",
    name: "Crop Farming",
    img: "https://images.unsplash.com/photo-1599058917212-d750089bc07a",
    description: "Cultivate cereals, pulses, oilseeds, millets and more."
  },
  {
    id: "vegetables",
    name: "Vegetable Farming",
    img: "https://images.unsplash.com/photo-1542834369-f10ebf06d3cb",
    description: "Grow tomato, brinjal, okra and leafy greens."
  },
  {
    id: "plantation",
    name: "Plantation",
    img: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6",
    description: "Coconut, areca, coffee, banana and other perennials."
  },
  {
    id: "dairy",
    name: "Dairy",
    img: "https://images.unsplash.com/photo-1588167056545-190d51189b9b",
    description: "Manage cows, buffaloes and milk production."
  },
  {
    id: "fisheries",
    name: "Fisheries",
    img: "https://images.unsplash.com/photo-1523861751938-7f78b6a18e83",
    description: "Rohu, Catla, Tilapia and freshwater aquaculture units."
  },
  {
    id: "poultry",
    name: "Poultry",
    img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4",
    description: "Broilers, layers or country chicken units."
  },
  {
    id: "goat",
    name: "Goat Rearing",
    img: "https://images.unsplash.com/photo-1626520343831-926d11e890d8",
    description: "Goats for meat or milk production."
  }
];

export default function CreateProductionUnit() {
  const navigate = useNavigate();
  const [loadingPractice, setLoadingPractice] = useState(null); // store selected ID

  const handleSelect = (practiceId) => {
    if (loadingPractice) return; // prevent double click

    let toastId;
    try {
      setLoadingPractice(practiceId);

      toastId = toast.loading("Setting up your selection...");

      // Save selected practice into wizard state
      localStorage.setItem("selected_practice", practiceId);

      toast.dismiss(toastId);
      toast.success("Practice selected!");

      navigate(`/farmer/production/select-category/${practiceId}`);
    } catch (err) {
      toast.dismiss(toastId);
      toast.error("Failed to select practice.");
      console.error("Practice select error:", err);
    } finally {
      setLoadingPractice(null);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Choose Your Farming Practice</h1>

      <div className="grid md:grid-cols-3 gap-6">
        {PRACTICES.map((p) => (
          <div
            key={p.id}
            onClick={() => handleSelect(p.id)}
            className={`cursor-pointer rounded-xl overflow-hidden shadow-lg transition bg-white border border-gray-200 
              ${
                loadingPractice === p.id
                  ? "opacity-70 pointer-events-none"
                  : "hover:shadow-2xl hover:-translate-y-1"
              }`}
          >
            <div className="h-40 w-full overflow-hidden">
              <img
                src={p.img}
                alt={p.name}
                className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
              />
            </div>

            <div className="p-4">
              <h2 className="text-xl font-semibold">{p.name}</h2>
              <p className="text-gray-600 text-sm mt-2">{p.description}</p>

              <button
                className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded disabled:bg-gray-400"
                disabled={loadingPractice === p.id}
              >
                {loadingPractice === p.id ? "Loading..." : "Select"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
