// frontend/context/UserContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase"; // your existing supabase client
import { api, setBackendToken } from "../services/api";


const UserContext = createContext();

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);          // supabase user object
  const [roles, setRoles] = useState([]);          // ["farmer","worker"]
  const [activeRole, setActiveRoleState] = useState(null); // "farmer"
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // optional: initialize supabase session if already logged in
    const ses = supabase.auth.getSession ? null : null; // keep compatibility
    // If you have a method to fetch current user, run it here and load roles
    // otherwise login flow will populate user and roles.
  }, []);

  const fetchRoles = async (profileId) => {
    // backend endpoint returns { roles: [...] }
    const res = await api.get(`/rbac/user/${profileId}/roles`);
    return res.data?.roles || [];
  };

  // Create backend session (create-session) which returns backend token
  const createBackendSession = async (profileId, chosenRole) => {
    setLoading(true);
    try {
      const res = await api.post("/auth/create-session", {
        user_id: profileId,
        active_role: chosenRole,
      });
      const token = res.data?.access_token;
      if (token) {
        setBackendToken(token);
        setActiveRoleState(chosenRole);
        return { token, roles: res.data.roles, active_role: res.data.active_role };
      } else {
        throw new Error("No backend token returned");
      }
    } finally {
      setLoading(false);
    }
  };

  // Switch active role (frontend uses /rbac/switch-role which returns a new token)
  const switchRole = async (profileId, newRole) => {
    setLoading(true);
    try {
      const res = await api.post("/rbac/switch-role", {
        user_id: profileId,
        new_active_role: newRole,
      });
      const token = res.data?.access_token;
      if (token) {
        setBackendToken(token);
        setActiveRoleState(newRole);
        return true;
      }
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    // Supabase sign out if used
    try {
      await supabase.auth.signOut();
    } catch (_) {}
    setUser(null);
    setRoles([]);
    setActiveRoleState(null);
    setBackendToken(null);
  };

  return (
    <UserContext.Provider
      value={{
        user,
        setUser,
        roles,
        setRoles,
        activeRole,
        setActiveRole: setActiveRoleState,
        createBackendSession,
        fetchRoles,
        switchRole,
        logout,
        loading,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
