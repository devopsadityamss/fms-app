import React, { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

// Hardcoded categories per practice (MVP) - will come from backend later
const CATEGORY_MAP = {
  crop: [
    { id: "cereals", name: "Cereals", img: "https://images.unsplash.com/photo-1500937386664-56e04c0b56d9" },
    { id: "pulses", name: "Pulses", img: "https://images.unsplash.com/photo-1518977676601-b53f82aba655" },
    { id: "oilseeds", name: "Oilseeds", img: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6" },
    { id: "millets", name: "Millets", img: "https://images.unsplash.com/photo-1591858353254-86b0d07f2599" },
    { id: "cashcrops", name: "Cash Crops", img: "https://images.unsplash.com/photo-1599058917212-d750089bc07a" }
  ],

  vegetables: [
    { id: "leafy", name: "Leafy Vegetables", img: "https://images.unsplash.com/photo-1524594154908-eddff6e690c5" },
    { id: "fruit", name: "Fruit Vegetables", img: "https://images.unsplash.com/photo-1592928302113-de6c3f2879d5" }
  ],

  plantation: [
    { id: "treecrops", name: "Tree Crops", img: "https://images.unsplash.com/photo-1441974231531-c6227db76b6e" }
  ],

  dairy: [
    { id: "cow", name: "Cows", img: "https://images.unsplash.com/photo-1517849845537-4d257902454a" },
    { id: "buffalo", name: "Buffaloes", img: "https://images.unsplash.com/photo-1588167056545-190d51189b9b" }
  ],

  fisheries: [
    { id: "freshwater", name: "Freshwater Fish", img: "https://images.unsplash.com/photo-1523861751938-7f78b6a18e83" }
  ],

  poultry: [
    { id: "broiler", name: "Broiler", img: "https://images.unsplash.com/photo-1567370627162-e76a2437c34c" },
    { id: "layer", name: "Layer", img: "https://images.unsplash.com/photo-1589927986089-35812388d1f4" }
  ],

  goat: [
    { id: "meat", name: "Meat Breeds", img: "https://images.unsplash.com/photo-1626520343831-926d11e890d8" }
  ]
};

export default function SelectPracticeCategory() {
  const { practiceId } = useParams();
  const navigate = useNavigate();

  const categories = CATEGORY_MAP[practiceId] || [];

  // Redirect if practiceId is invalid (ensures stable flow)
  useEffect(() => {
    if (!CATEGORY_MAP[practiceId]) {
      navigate("/farmer/production/create");
    }
  }, [practiceId, navigate]);

  const handleSelect = (categoryId) => {
    // Persist selected category for next steps
    localStorage.setItem("selected_category", categoryId);

    navigate(`/farmer/production/select-options/${practiceId}/${categoryId}`);
  };

  return (
    <div className="p-8">

      {/* Header with back button */}
      <div className="flex items-center gap-4 mb-6">
        <button
          className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>

        <h1 className="text-3xl font-bold">Choose Category</h1>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {categories.map((cat) => (
          <div
            key={cat.id}
            onClick={() => handleSelect(cat.id)}
            className="cursor-pointer rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1 bg-white border border-gray-200"
          >
            <div className="h-40 w-full overflow-hidden">
              <img
                src={cat.img}
                alt={cat.name}
                className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
              />
            </div>

            <div className="p-4">
              <h2 className="text-xl font-semibold">{cat.name}</h2>

              <button className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
                Select
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
