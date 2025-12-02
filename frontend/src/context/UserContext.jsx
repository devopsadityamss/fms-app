import React, { createContext, useEffect, useState, useContext } from "react";
import { supabase } from "../lib/supabase";
import { api } from "../api/client";

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  // Sync Supabase session
  useEffect(() => {
    const session = supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user || null);
      // attach token to API client
      if (data.session?.access_token) {
        api.defaults.headers.common.Authorization =
          `Bearer ${data.session.access_token}`;
      }
    });

    // Listen for login/logout
    const { data: authListener } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user || null);
        if (session?.access_token) {
          api.defaults.headers.common.Authorization =
            `Bearer ${session.access_token}`;
        } else {
          delete api.defaults.headers.common.Authorization;
        }
      }
    );

    return () => authListener.subscription.unsubscribe();
  }, []);

  return (
    <UserContext.Provider value={{ user }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
