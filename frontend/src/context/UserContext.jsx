// frontend/context/UserContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { api, setBackendToken } from "../services/api";

const UserContext = createContext();

export function UserProvider({ children }) {
  const [supabaseUser, setSupabaseUser] = useState(null); // <-- NEW
  const [user, setUser] = useState(null);                 // backend user (from JWT)
  const [roles, setRoles] = useState([]);
  const [activeRole, setActiveRoleState] = useState(null);
  const [loading, setLoading] = useState(false);

  // Listen for Supabase login/logout
  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setSupabaseUser(session.user); // <-- STORE USER ID HERE
      } else {
        setSupabaseUser(null);
      }
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  const fetchRoles = async (profileId) => {
    const res = await api.get(`/rbac/user/${profileId}/roles`);
    return res.data?.roles || [];
  };

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
        setRoles(res.data.roles);

        // backend user object
        setUser({ user_id: profileId });
      }
      return res.data;
    } finally {
      setLoading(false);
    }
  };

  const switchRole = async (profileId, newRole) => {
    setLoading(true);
    try {
      const res = await api.post("/rbac/switch-role", {
        user_id: profileId,
        new_active_role: newRole,
      });

      if (res.data?.access_token) {
        setBackendToken(res.data.access_token);
        setActiveRoleState(newRole);
        return true;
      }
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (_) {}

    setSupabaseUser(null);
    setUser(null);
    setRoles([]);
    setActiveRoleState(null);
    setBackendToken(null);
  };

  return (
    <UserContext.Provider
      value={{
        supabaseUser,   // <-- IMPORTANT EXPORT
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
