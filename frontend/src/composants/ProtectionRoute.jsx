import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexte/AuthContext";

export default function ProtectionRoute() {
  const { connecte, initialisation } = useAuth();
  const location = useLocation();
  if (initialisation) return <div className="p-6 text-center" role="status">Vérification de la session…</div>;
  return connecte ? <Outlet /> : <Navigate to="/connexion" replace state={{ depuis: location.pathname }} />;
}
