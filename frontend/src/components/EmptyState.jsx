export default function EmptyState({ title, description }) {
  return (
    <div className="text-center p-10 text-slate-500">
      <div className="text-4xl mb-3">📭</div>
      <h2 className="font-semibold text-lg">{title}</h2>
      <p className="text-slate-400 text-sm mt-1">{description}</p>
    </div>
  );
}
