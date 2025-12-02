export default function Input({ className = "", ...rest }) {
  return (
    <input
      className={`w-full rounded-md border border-slate-300 p-2 text-sm focus:ring focus:ring-indigo-200 focus:outline-none ${className}`}
      {...rest}
    />
  );
}
