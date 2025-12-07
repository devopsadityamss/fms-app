// frontend/context/UserContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { api, setBackendToken } from "../services/api";

const UserContext = createContext();

export function UserProvider({ children }) {
  const [supabaseUser, setSupabaseUser] = useState(null);
  const [user, setUser] = useState(null);                 // backend user (from JWT)
  const [roles, setRoles] = useState([]);
  const [activeRole, setActiveRoleState] = useState(null);
  const [loading, setLoading] = useState(false);

  // Listen for Supabase login/logout
  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setSupabaseUser(session.user);
      } else {
        setSupabaseUser(null);
      }
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  // Restore activeRole on page reload
  useEffect(() => {
    const saved = localStorage.getItem("activeRole");
    if (saved && !activeRole) {
      setActiveRoleState(saved);
    }
  }, []);

  const fetchRoles = async (profileId) => {
    const res = await api.get(`/rbac/user/${profileId}/roles`);
    return res.data?.roles || [];
  };

  // ⭐ ADDED: Load roles automatically when supabaseUser is ready
  useEffect(() => {
    async function loadUserRoles() {
      if (!supabaseUser?.id) return;
      const fetched = await fetchRoles(supabaseUser.id);
      setRoles(fetched);               // <-- ADDED
    }

    loadUserRoles();
  }, [supabaseUser]);                 // <-- ADDED

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
        localStorage.setItem("activeRole", chosenRole);   // <-- ADDED

        setRoles(res.data.roles || []); // <-- UPDATED
        setUser({ user_id: profileId });
      }
      return res.data;
    } finally {
      setLoading(false);
    }
  };

  // CLEAN + CORRECT switchRole → now automatically uses supabaseUser.id
  const switchRole = async (newRole) => {
    if (!supabaseUser?.id) return false;

    setLoading(true);
    try {
      const res = await api.post("/rbac/switch-role", {
        user_id: supabaseUser.id,
        new_active_role: newRole,
      });

      if (res.data?.access_token) {
        setBackendToken(res.data.access_token);
        setActiveRoleState(newRole);
        localStorage.setItem("activeRole", newRole);       // <-- ADDED
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
    localStorage.removeItem("activeRole");                 // <-- CLEAN RESET
  };

  return (
    <UserContext.Provider
      value={{
        supabaseUser,
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
