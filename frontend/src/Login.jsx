// src/Login.jsx
import React, { useState } from 'react'
import { supabase } from './lib/supabaseClient'

export default function Login() {
  const [email, setEmail] = useState('alice+demo@example.com')
  const [password, setPassword] = useState('Password123!')

  const signIn = async () => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return alert(error.message)
    console.log('signed in', data)
    // store session and use access_token in API calls to FastAPI if needed
  }

  return (
    <div>
      <input value={email} onChange={e=>setEmail(e.target.value)} />
      <input value={password} type="password" onChange={e=>setPassword(e.target.value)} />
      <button onClick={signIn}>Sign in</button>
    </div>
  )
}
