import { Navigate } from "react-router-dom";
import { useUser } from "../context/UserContext";

export default function ProtectedRoute({ children }) {
  const backendToken = localStorage.getItem("fms_backend_token");
  const { roles, activeRole, user } = useUser();

  // Not authenticated → login
  if (!backendToken || backendToken.length < 10) {
    return <Navigate to="/login" replace />;
  }

  // User exists but has ZERO roles → role registration
  if (user && roles.length === 0) {
    return <Navigate to="/register-roles" replace />;
  }

  // User has roles but has NOT selected one → show dashboard
  if (user && roles.length > 0 && !activeRole) {
    return <Navigate to="/" replace />;
  }

  return children;
}
