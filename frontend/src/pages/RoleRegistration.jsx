import React, { useEffect, useState } from "react";
import { api } from "../services/api";
import { useUser } from "../context/UserContext";
import RoleSelector from "../components/RoleSelector";

export default function RoleRegistration() {
  const { user, supabaseUser } = useUser();   // <-- IMPORTANT
  const [allRoles, setAllRoles] = useState([]);
  const [selected, setSelected] = useState([]);
  const [showSelector, setShowSelector] = useState(false);
  const [error, setError] = useState(null);

  // Fix: Always pull ID from supabaseUser.id (works for onboarding)
  const userId = user?.user_id || supabaseUser?.id;

  useEffect(() => {
    async function fetchRoles() {
      try {
        const res = await api.get("/rbac/roles");
        setAllRoles(res.data);
      } catch (err) {
        setError("Failed to load roles");
      }
    }
    fetchRoles();
  }, []);

  const toggleRole = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (!userId) {
      setError("User ID missing — login again.");
      return;
    }

    if (selected.length === 0) {
      setError("Please select at least one role.");
      return;
    }

    try {
      await api.post("/rbac/assign-roles-bulk", {
        user_id: userId,      // <-- FIXED (now guaranteed)
        role_ids: selected,
      });

      setShowSelector(true);
    } catch (err) {
      console.error(err);
      setError("Failed to assign roles");
    }
  };

  if (showSelector) {
    const selectedNames = allRoles
      .filter((r) => selected.includes(r.id))
      .map((r) => r.name);

    return (
      <RoleSelector
        roles={selectedNames}
        onSelect={() => {}}
        onCancel={() => {}}
      />
    );
  }

  return (
    <div style={{ padding: 20, maxWidth: 650, margin: "40px auto" }}>
      <h2>Select Your Roles</h2>
      <p style={{ marginBottom: 20 }}>
        Choose one or more roles that match how you want to use the app.
      </p>

      {error && <div style={{ color: "red", marginBottom: 10 }}>{error}</div>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 16,
        }}
      >
        {allRoles.map((role) => {
          const isSelected = selected.includes(role.id);
          return (
            <div
              key={role.id}
              onClick={() => toggleRole(role.id)}
              style={{
                padding: 20,
                cursor: "pointer",
                borderRadius: 10,
                textAlign: "center",
                border: `2px solid ${isSelected ? "#2563eb" : "#ccc"}`,
                background: isSelected ? "#e0ecff" : "#fff",
                boxShadow: "0 4px 8px rgba(0,0,0,0.08)",
              }}
            >
              <b>
                {role.name
                  .replace("_", " ")
                  .replace(/\b\w/g, (c) => c.toUpperCase())}
              </b>
            </div>
          );
        })}
      </div>

      <button
        onClick={handleSubmit}
        style={{
          marginTop: 25,
          padding: "10px 20px",
          fontSize: 16,
          cursor: "pointer",
        }}
      >
        Continue
      </button>
    </div>
  );
}
