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
      }}
    >
      <div>FMS</div>

      <div style={{ display: "flex", gap: 20 }}>
        <div>Role: {activeRole}</div>
        <button
          onClick={() => setShow(true)}
          style={{
            background: "white",
            color: "#1e293b",
            padding: "6px 12px",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          Switch Role
        </button>
      </div>

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
