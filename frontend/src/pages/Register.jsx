import React, { useState } from "react";
import { supabase } from "../lib/supabase";
import { api } from "../services/api";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      // 1. Create user in Supabase Auth
      const { data, error: signupError } = await supabase.auth.signUp({
        email,
        password,
      });

      if (signupError) {
        setError(signupError.message);
        return;
      }

      const user = data?.user;
      if (!user) {
        setError("Signup succeeded but no user returned.");
        return;
      }

      // 2. Insert SUPABASE user into your backend profiles table
      await api.post("/auth/create-profile", {
        id: user.id,
        email,
        full_name: fullName,
      });

      // 3. Show success + redirect
      setSuccess(true);

      setTimeout(() => {
        window.location.href = "/login";
      }, 1200);
    } catch (err) {
      console.error(err);
      setError("Signup failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-300 to-green-600 p-4">

      {/* CENTER CARD */}
      <div className="bg-white/90 backdrop-blur-md p-10 rounded-2xl shadow-xl w-full max-w-md border">

        {/* LOGO + TITLE */}
        <div className="text-center mb-8">
          <div className="text-4xl font-extrabold text-green-700 tracking-tight">
            🌿 FMS
          </div>
          <p className="text-gray-600 mt-1 text-sm">
            Create your account to get started
          </p>
        </div>

        {/* SUCCESS MESSAGE */}
        {success && (
          <div className="mb-4 p-3 text-green-700 bg-green-100 rounded text-center font-semibold">
            Account created! Redirecting...
          </div>
        )}

        {/* ERROR MESSAGE */}
        {error && (
          <div className="mb-4 p-3 text-red-700 bg-red-100 rounded text-center font-semibold">
            {error}
          </div>
        )}

        {/* FORM */}
        <form onSubmit={handleSignup}>
          <input
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full p-3 mb-4 border rounded-lg focus:ring-2 focus:ring-green-500 focus:outline-none"
          />

          <input
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-3 mb-4 border rounded-lg focus:ring-2 focus:ring-green-500 focus:outline-none"
          />

          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-3 mb-6 border rounded-lg focus:ring-2 focus:ring-green-500 focus:outline-none"
          />

          {/* REGISTER BUTTON */}
          <button
            type="submit"
            className="w-full bg-green-700 hover:bg-green-800 text-white p-3 rounded-lg font-semibold transition"
          >
            Create Account
          </button>

          {/* LOGIN LINK */}
          <button
            type="button"
            onClick={() => (window.location.href = "/login")}
            className="w-full mt-4 bg-white text-green-700 border border-green-700 p-3 rounded-lg font-semibold hover:bg-green-50 transition"
          >
            Already have an account? Log in
          </button>
        </form>
      </div>
    </div>
  );
}
