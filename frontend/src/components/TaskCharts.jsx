import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from "recharts";

const COLORS = ["#60A5FA", "#FBBF24", "#34D399", "#F87171"];

export function TaskStatusPie({ data }) {
  const processed = [
    { name: 'Pending', value: data.filter(d => d.status === 'pending').length },
    { name: 'In Progress', value: data.filter(d => d.status === 'in_progress').length },
    { name: 'Completed', value: data.filter(d => d.status === 'completed').length },
  ];
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={processed} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70} paddingAngle={2}>
          {processed.map((entry, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function TasksByProjectBar({ projects, tasks }) {
  const data = projects.map(p => ({ name: p.name, value: tasks.filter(t => t.project_id === p.id).length }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data}>
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill="#60A5FA" />
      </BarChart>
    </ResponsiveContainer>
  );
}
