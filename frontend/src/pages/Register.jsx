import React, { useState } from "react";
import { supabase } from "../lib/supabase";
import { useNavigate, Link } from "react-router-dom";

export default function Register() {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleRegister = async () => {
    setError("");
    const { error } = await supabase.auth.signUp({
      email,
      password: pass,
    });
    if (error) setError(error.message);
    else navigate("/"); // auto-login because Supabase handles session
  };

  return (
    <div className="flex items-center justify-center h-screen bg-slate-100">
      <div className="bg-white p-6 shadow rounded w-96">
        <h2 className="text-2xl font-semibold mb-4">Register</h2>

        {error && <p className="text-red-600 mb-2">{error}</p>}

        <input
          className="w-full p-2 border rounded mb-3"
          placeholder="Email"
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          className="w-full p-2 border rounded mb-3"
          placeholder="Password"
          onChange={(e) => setPass(e.target.value)}
        />

        <button
          onClick={handleRegister}
          className="w-full bg-indigo-600 text-white p-2 rounded"
        >
          Register
        </button>

        <p className="text-sm mt-3">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-600">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
