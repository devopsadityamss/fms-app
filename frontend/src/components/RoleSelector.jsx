import React from "react";
import { useUser } from "../context/UserContext";

export default function RoleSelector({ roles, onSelect, onCancel }) {
  const { supabaseUser, createBackendSession } = useUser();

  const handleSelect = async (role) => {
    if (!supabaseUser?.id) {
      alert("User ID missing — please log in again.");
      window.location.href = "/login";
      return;
    }

    if (roles.length === 0) {
      try {
        await createBackendSession(supabaseUser.id, role);
        window.location.href = "/";
      } catch (err) {
        console.error(err);
        alert("Failed to activate role.");
      }
      return;
    }

    if (onSelect) onSelect(role);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          padding: 25,
          background: "#fff",
          borderRadius: 10,
          width: 300,
          textAlign: "center",
        }}
      >
        <h3 style={{ marginBottom: 20, color: "#333" }}>Select Your Role</h3>

        {roles.map((roleItem) => {
          const label =
            typeof roleItem === "string"
              ? roleItem
              : roleItem?.role || "";

          return (
            <div
              key={label}
              onClick={() => handleSelect(label)}
              style={{
                padding: 12,
                marginBottom: 10,
                border: "1px solid #ccc",
                borderRadius: 6,
                cursor: "pointer",
                fontWeight: "bold",
                color: "#222",               // ⭐ FIX: visible text color
                background: "#f9f9f9",       // (optional but looks better)
              }}
            >
              {label.toUpperCase()}
            </div>
          );
        })}

        <button
          onClick={onCancel}
          style={{
            marginTop: 10,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "#444",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
