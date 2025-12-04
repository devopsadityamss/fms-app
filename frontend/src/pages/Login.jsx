// frontend/pages/Login.jsx
import React, { useState } from "react";
import { supabase } from "../lib/supabase";
import { useUser } from "../context/UserContext";
import RoleSelector from "../components/RoleSelector";
import { api } from "../services/api";
import { useNavigate } from "react-router-dom";     // <-- ADDED

export default function Login() {
  const navigate = useNavigate();                  // <-- ADDED

  const { setUser, fetchRoles, createBackendSession, setRoles } = useUser();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showRoleSelector, setShowRoleSelector] = useState(false);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [profileId, setProfileId] = useState(null);
  const [error, setError] = useState(null);

  const handleSupabaseLogin = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const { data, error: loginError } =
        await supabase.auth.signInWithPassword({
          email,
          password,
        });

      if (loginError) {
        setError(loginError.message || "Login failed");
        return;
      }

      const user = data?.user ?? data?.session?.user;

      if (!user) {
        setError("No user returned from Supabase");
        return;
      }

      setUser(user);

      const userId = user.id;
      setProfileId(userId);

      // ---- Fetch roles ----
      let rolesList = [];
      try {
        const rolesResponse = await api.get(`/rbac/user/${userId}/roles`);
        rolesList = rolesResponse.data?.roles || [];
        setAvailableRoles(rolesList);
        setRoles(rolesList);
      } catch (err) {
        console.error(err);
        setError("Failed to fetch roles from backend");
        return;
      }

      // ---- Handle role count ----
      if (rolesList.length === 0) {
        navigate("/register-roles"); // <-- FIXED
        return;
      }

      if (rolesList.length === 1) {
        const chosen = rolesList[0];

        try {
          await createBackendSession(userId, chosen);
          navigate("/", { replace: true });        // <-- FIXED
        } catch (e2) {
          console.error(e2);
          setError("Failed to create backend session");
        }
        return;
      }

      // multiple roles
      setShowRoleSelector(true);
    } catch (err) {
      console.error(err);
      setError("Login failed");
    }
  };

  // ---- role selection handler ----
  const handleRoleSelect = async (role) => {
    if (!profileId) {
      setError("Profile ID missing");
      return;
    }

    setShowRoleSelector(false);

    try {
      await createBackendSession(profileId, role);
      navigate("/", { replace: true });            // <-- FIXED
    } catch (err) {
      console.error(err);
      setError("Failed to create backend session");
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 520, margin: "40px auto" }}>
      <h2>Login</h2>

      <form onSubmit={handleSupabaseLogin}>
        <div style={{ marginBottom: 8 }}>
          <input
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", padding: 8 }}
          />
        </div>

        <div style={{ marginBottom: 8 }}>
          <input
            placeholder="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: 8 }}
          />
        </div>

        <div>
          <button type="submit" style={{ padding: "8px 12px" }}>
            Login
          </button>
        </div>

        {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}
      </form>

      {showRoleSelector && (
        <RoleSelector
          roles={availableRoles}
          onSelect={handleRoleSelect}
          onCancel={() => setShowRoleSelector(false)}
        />
      )}
    </div>
  );
}
