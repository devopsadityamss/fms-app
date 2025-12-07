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

      const resp = await api.get(`/rbac/user/${userId}/roles`);
      const rolesList = resp.data?.roles || [];

      setRoles(rolesList);
      setAvailableRoles(rolesList);

      if (rolesList.length === 0) {
        window.location.href = "/register-roles";
        return;
      }

      if (rolesList.length === 1) {
        await createBackendSession(userId, rolesList[0]);
        window.location.href = "/";
        return;
      }

      setShowRoleSelector(true);
    } catch (err) {
      console.error(err);
      setError("Login failed");
    }
  };

  const handleRoleSelect = async (role) => {
    setShowRoleSelector(false);
    await createBackendSession(profileId, role);
    window.location.href = "/";
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-gradient-to-tr from-emerald-300 via-teal-200 to-green-300 overflow-hidden">

      {/* Floating animated orbs */}
      <div className="absolute w-[500px] h-[500px] bg-white/20 rounded-full blur-3xl top-[-100px] left-[-100px] animate-pulse"></div>
      <div className="absolute w-[400px] h-[400px] bg-green-400/30 rounded-full blur-2xl bottom-[-80px] right-[-80px] animate-pulse"></div>

      {/* Glass card */}
      <div className="relative z-10 w-full max-w-lg backdrop-blur-2xl bg-white/30 p-10 rounded-3xl shadow-2xl border border-white/40">

        {/* App logo */}
        <div className="w-16 h-16 mx-auto bg-white/70 rounded-2xl shadow-md flex items-center justify-center mb-4">
          <span className="text-2xl font-bold text-emerald-700">FMS</span>
        </div>

        {/* Headings */}
        <h1 className="text-4xl font-extrabold text-center text-slate-800 mb-2 tracking-tight">
          Welcome Back
        </h1>
        <p className="text-center text-slate-700 mb-8 text-lg">
          Sign in to continue to your dashboard
        </p>

        {/* Login Form */}
        <form onSubmit={handleSupabaseLogin} className="space-y-5">

          <input
            type="email"
            placeholder="Email address"
            className="w-full p-4 rounded-2xl bg-white/60 border border-white/40 focus:outline-none focus:ring-4 focus:ring-emerald-400 text-slate-800 placeholder-slate-500 shadow-inner"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Password"
            className="w-full p-4 rounded-2xl bg-white/60 border border-white/40 focus:outline-none focus:ring-4 focus:ring-emerald-400 text-slate-800 placeholder-slate-500 shadow-inner"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && (
            <div className="text-red-700 text-center font-medium text-sm">
              {error}
            </div>
          )}

          {/* Login Button */}
          <button
            type="submit"
            className="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-2xl shadow-xl transition transform hover:scale-[1.02]"
          >
            Login
          </button>

          {/* Huge SIGNUP button */}
          <button
            type="button"
            onClick={() => (window.location.href = "/register")}
            className="w-full py-3 bg-white/70 text-emerald-900 font-semibold rounded-2xl border border-emerald-500 shadow-lg hover:bg-white hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            Create an Account
          </button>

        </form>
      </div>

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
