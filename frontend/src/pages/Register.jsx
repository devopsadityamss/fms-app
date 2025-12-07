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
      const { data, error: signupError } =
        await supabase.auth.signUp({
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
      }, 1000);
    } catch (err) {
      console.error(err);
      setError("Signup failed");
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 520, margin: "40px auto" }}>
      <h2>Create Account</h2>

      {success && (
        <div style={{ color: "green", marginBottom: 10 }}>
          Account created! Redirecting to login…
        </div>
      )}

      {error && (
        <div style={{ color: "red", marginBottom: 10 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSignup}>
        <input
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        />
        <input
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        />

        <button type="submit" style={{ padding: "8px 12px" }}>
          Register
        </button>
      </form>

      {/* Optional: Add a login link for users who already have an account */}
      <div style={{ marginTop: 15, textAlign: "center" }}>
        <a href="/login" style={{ color: "blue", cursor: "pointer" }}>
          Already have an account? Log in
        </a>
      </div>
    </div>
  );
}