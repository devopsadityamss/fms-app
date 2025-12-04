import { Navigate } from "react-router-dom";
import { useUser } from "../context/UserContext";
import { getBackendToken } from "../services/api";   // ✅ ADDED

export default function ProtectedRoute({ children }) {
  // get token from api helper (preferred)
  const storedToken = getBackendToken();

  // fallback: direct localStorage check
  const backendToken =
    storedToken || localStorage.getItem("fms_backend_token");

  // context fallback (not used for auth, but don’t remove)
  const { activeRole } = useUser();

  // Robust authentication check
  const isAuthed = backendToken && backendToken.length > 10;

  return isAuthed ? children : <Navigate to="/login" replace />;
}
