import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { adminApi } from "./adminApi";

const AdminAuthContext = createContext(null);

function lireAdmin() {
  try { return JSON.parse(localStorage.getItem("administrateur") || "null"); }
  catch { return null; }
}

export function AdminAuthProvider({ children }) {
  const [administrateur, setAdministrateur] = useState(lireAdmin);
  const [connecte, setConnecte] = useState(() => Boolean(localStorage.getItem("admin_access") && lireAdmin()));

  useEffect(() => {
    const expirer = () => { setConnecte(false); setAdministrateur(null); };
    window.addEventListener("admin-session-expiree", expirer);
    return () => window.removeEventListener("admin-session-expiree", expirer);
  }, []);

  const connexion = useCallback(async (email, motDePasse) => {
    const { data } = await adminApi.post("/api/admin/auth/connexion/", { email: email.trim().toLowerCase(), mot_de_passe: motDePasse });
    if (!data.administrateur?.super_admin && !Array.isArray(data.administrateur?.permissions)) {
      throw new Error("Ce compte n'a pas accès au back-office.");
    }
    localStorage.setItem("admin_access", data.access);
    localStorage.setItem("admin_refresh", data.refresh);
    localStorage.setItem("administrateur", JSON.stringify(data.administrateur));
    setAdministrateur(data.administrateur);
    setConnecte(true);
  }, []);

  const deconnexion = useCallback(() => {
    localStorage.removeItem("admin_access");
    localStorage.removeItem("admin_refresh");
    localStorage.removeItem("administrateur");
    setAdministrateur(null);
    setConnecte(false);
  }, []);

  const valeur = useMemo(() => ({ administrateur, connecte, connexion, deconnexion }), [administrateur, connecte, connexion, deconnexion]);
  return <AdminAuthContext.Provider value={valeur}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}

export function aPermission(administrateur, permission) {
  return Boolean(administrateur?.super_admin || administrateur?.permissions?.includes("*") || administrateur?.permissions?.includes(permission));
}
