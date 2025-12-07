import React, { useState } from "react";
import { useUser } from "../context/UserContext";
import RoleSelector from "./RoleSelector";

export default function Navbar() {
  const { roles, activeRole, switchRole } = useUser();
  const [show, setShow] = useState(false);

  const handleSelect = async (role) => {
    await switchRole(role);
    setShow(false);
  };

  return (
    <div
      style={{
        padding: "12px 20px",
        background: "#1e293b",
        color: "white",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",             // <-- ADDED for proper alignment
      }}
    >
      <div style={{ fontWeight: "bold", fontSize: 18 }}>FMS</div>

      <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
        {/* ⭐ Active Role Badge (clean, modern, readable) */}
        <div
          style={{
            background: "#10b98120",
            border: "1px solid #10b981",
            padding: "6px 14px",
            borderRadius: 20,
            fontWeight: "bold",
            color: "#34d399",
            minWidth: 140,
            textAlign: "center",
          }}
        >
          {activeRole
            ? `Active Role: ${activeRole.toUpperCase()}`
            : "No Role Selected"}
        </div>

        {/* ⭐ Switch Role Button (unchanged functionality) */}
        <button
          onClick={() => setShow(true)}
          style={{
            background: "white",
            color: "#1e293b",
            padding: "6px 12px",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          Switch Role
        </button>
      </div>

      {/* ⭐ Role Selector Modal */}
      {show && (
        <RoleSelector
          roles={roles}
          onSelect={handleSelect}
          onCancel={() => setShow(false)}
        />
      )}
    </div>
  );
}
