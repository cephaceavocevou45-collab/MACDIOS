import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, initialiserCSRF } from "../api";

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [administrateur, setAdministrateur] = useState(null);
  const [connecte, setConnecte] = useState(false);
  const [initialisation, setInitialisation] = useState(true);

  useEffect(() => {
    let actif = true;
    const sessionExpiree = () => { setConnecte(false); setAdministrateur(null); };
    window.addEventListener("session-expiree", sessionExpiree);
    (async () => {
      try {
        await initialiserCSRF();
        const { data } = await api.get("/api/auth/session/");
        if (actif && data.administrateur) {
          setAdministrateur(data.administrateur);
          setConnecte(true);
        }
      } catch { /* Une visite sans session reste sur l'écran de connexion. */ }
      finally { if (actif) setInitialisation(false); }
    })();
    return () => { actif = false; window.removeEventListener("session-expiree", sessionExpiree); };
  }, []);

  const connexion = useCallback(async (email, motDePasse) => {
    await initialiserCSRF();
    const { data } = await api.post("/api/admin/auth/connexion/", {
      email: email.trim().toLowerCase(), mot_de_passe: motDePasse,
    });
    if (!data.administrateur?.super_admin && !Array.isArray(data.administrateur?.permissions)) {
      throw new Error("Ce compte n'a pas accès au back-office.");
    }
    setAdministrateur(data.administrateur);
    setConnecte(true);
  }, []);

  const deconnexion = useCallback(async () => {
    try { await api.post("/api/auth/deconnexion/", {}); } finally {
      setAdministrateur(null);
      setConnecte(false);
    }
  }, []);

  const valeur = useMemo(() => ({ administrateur, connecte, initialisation, connexion, deconnexion }), [administrateur, connecte, initialisation, connexion, deconnexion]);
  return <AdminAuthContext.Provider value={valeur}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth() { return useContext(AdminAuthContext); }

export function aPermission(administrateur, permission) {
  return Boolean(administrateur?.super_admin || administrateur?.permissions?.includes("*") || administrateur?.permissions?.includes(permission));
}
