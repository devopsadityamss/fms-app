import React from "react";
import { useNavigate } from "react-router-dom";

// Temporary hardcoded practices (later moved to backend)
const PRACTICES = [
  {
    id: "crop",
    name: "Crop Farming",
    img: "https://images.unsplash.com/photo-1599058917212-d750089bc07a", // paddy field
    description: "Cultivate cereals, pulses, oilseeds, millets and more."
  },
  {
    id: "vegetables",
    name: "Vegetable Farming",
    img: "https://images.unsplash.com/photo-1542834369-f10ebf06d3cb",
    description: "Grow fresh vegetables like tomato, brinjal, okra and leafy greens."
  },
  {
    id: "plantation",
    name: "Plantation",
    img: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6",
    description: "Long-term crops such as coconut, areca, coffee, and banana."
  },
  {
    id: "dairy",
    name: "Dairy",
    img: "https://images.unsplash.com/photo-1588167056545-190d51189b9b",
    description: "Raise and manage cows, buffaloes, and milk production."
  },
  {
    id: "fisheries",
    name: "Fisheries",
    img: "https://images.unsplash.com/photo-1523861751938-7f78b6a18e83",
    description: "Fish ponds for species like Rohu, Catla, Tilapia and more."
  },
  {
    id: "poultry",
    name: "Poultry",
    img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4",
    description: "Manage broilers, layers or country chicken units."
  },
  {
    id: "goat",
    name: "Goat Rearing",
    img: "https://images.unsplash.com/photo-1626520343831-926d11e890d8",
    description: "Breed goats for meat or milk production."
  }
];

export default function CreateProductionUnit() {
  const navigate = useNavigate();

  const handleSelect = (practiceId) => {
    navigate(`/production/select-category/${practiceId}`);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Choose Your Farming Practice</h1>

      <div className="grid md:grid-cols-3 gap-6">
        {PRACTICES.map((p) => (
          <div
            key={p.id}
            onClick={() => handleSelect(p.id)}
            className="cursor-pointer rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1 bg-white"
          >
            <div className="h-40 w-full overflow-hidden">
              <img
                src={p.img}
                alt={p.name}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="p-4">
              <h2 className="text-xl font-semibold">{p.name}</h2>
              <p className="text-gray-600 text-sm mt-2">{p.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
