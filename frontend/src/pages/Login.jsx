// frontend/pages/Login.jsx
import React, { useState } from "react";
import { supabase } from "../lib/supabase";
import { useUser } from "../context/UserContext";
import RoleSelector from "../components/RoleSelector";
import { api } from "../services/api";

export default function Login() {
  const { setUser, setRoles, createBackendSession } = useUser();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showRoleSelector, setShowRoleSelector] = useState(false);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [profileId, setProfileId] = useState(null);
  const [error, setError] = useState(null);

  // ----------------------------------------------------
  // HANDLE SUPABASE LOGIN
  // ----------------------------------------------------
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

      // ----------------------------------------------------
      // FETCH ROLES FROM BACKEND
      // ----------------------------------------------------
      const resp = await api.get(`/rbac/user/${userId}/roles`);
      const rolesList = resp.data?.roles || [];
      setRoles(rolesList);
      setAvailableRoles(rolesList);

      // ----------------------------------------------------
      // CASE 1 — No roles → go to registration page
      // ----------------------------------------------------
      if (rolesList.length === 0) {
        window.location.href = "/register-roles";
        return;
      }

      // ----------------------------------------------------
      // CASE 2 — One role → auto-create backend session
      // ----------------------------------------------------
      if (rolesList.length === 1) {
        const chosen = rolesList[0];
        try {
          await createBackendSession(userId, chosen);
          window.location.href = "/";
        } catch (e) {
          console.error(e);
          setError("Failed to create backend session");
        }
        return;
      }

      // ----------------------------------------------------
      // CASE 3 — Multiple roles → show RoleSelector
      // ----------------------------------------------------
      setShowRoleSelector(true);
    } catch (err) {
      console.error(err);
      setError("Login failed");
    }
  };

  // ----------------------------------------------------
  // HANDLE ROLE SELECTION
  // ----------------------------------------------------
  const handleRoleSelect = async (role) => {
    if (!profileId) {
      setError("Profile ID missing");
      return;
    }

    setShowRoleSelector(false);

    try {
      await createBackendSession(profileId, role);
      window.location.href = "/";
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

        <button type="submit" style={{ padding: "8px 12px" }}>
          Login
        </button>

        {/* ←←← ONLY THIS PART WAS ADDED ←←← */}
        <div style={{ marginTop: 10 }}>
          <a href="/register" style={{ color: "blue", cursor: "pointer" }}>
            Don't have an account? Sign up
          </a>
        </div>
        {/* ←←← END OF ADDITION ←←← */}

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