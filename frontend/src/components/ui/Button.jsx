export default function Button({ children, variant = "primary", className = "", ...rest }) {
  const base =
    "px-4 py-2 rounded-md text-sm font-medium transition focus:ring focus:ring-indigo-300";

  const variants = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700",
    subtle: "bg-slate-100 hover:bg-slate-200 text-slate-800",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}
