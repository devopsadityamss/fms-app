// frontend/components/RoleSelector.jsx
import React from "react";

export default function RoleSelector({ roles = [], onSelect, onCancel }) {
  return (
    <div style={overlayStyle}>
      <div style={boxStyle}>
        <h3>Select Your Role</h3>

        {roles.length === 0 && (
          <p style={{ color: "red" }}>No roles available.</p>
        )}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            marginTop: 12,
          }}
        >
          {roles.map((r) => (
            <button
              key={r}
              onClick={() => onSelect(r)}
              style={{
                padding: "10px 14px",
                cursor: "pointer",
                borderRadius: 6,
              }}
            >
              {r.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 12 }}>
          <button onClick={onCancel} style={{ opacity: 0.7 }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

const overlayStyle = {
  position: "fixed",
  left: 0,
  top: 0,
  right: 0,
  bottom: 0,
  background: "rgba(0,0,0,0.35)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 9999,
};

const boxStyle = {
  width: 360,
  background: "#fff",
  padding: 20,
  borderRadius: 8,
  boxShadow: "0 6px 18px rgba(0,0,0,0.12)",
};
