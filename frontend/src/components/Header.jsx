import React, { useEffect, useState } from "react";
export default function Header() {
  const [isDark, setIsDark] = useState(() => localStorage.getItem('fms_dark') === '1');

  useEffect(() => {
    if (isDark) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
    localStorage.setItem('fms_dark', isDark ? '1' : '0');
  }, [isDark]);

  return (
    <header className="bg-white dark:bg-slate-800 shadow p-4 flex items-center justify-between">
      <h2 className="text-lg font-semibold dark:text-white">FMS App</h2>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsDark(!isDark)}
          className="px-2 py-1 rounded border dark:border-slate-700"
        >
          {isDark ? "🌙" : "☀️"}
        </button>
        <div className="w-8 h-8 rounded-full bg-slate-400"></div>
      </div>
    </header>
  );
}
