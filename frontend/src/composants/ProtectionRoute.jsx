import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexte/AuthContext";

export default function ProtectionRoute() {
  const { connecte } = useAuth();
  const location = useLocation();
  return connecte ? <Outlet /> : <Navigate to="/connexion" replace state={{ depuis: location.pathname }} />;
}
