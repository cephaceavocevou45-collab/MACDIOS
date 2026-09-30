import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [connecte, setConnecte] = useState(() => Boolean(localStorage.getItem("access")));
  const [commercant, setCommercant] = useState(() => {
    try { return JSON.parse(localStorage.getItem("commercant") || "null"); }
    catch { return null; }
  });

  useEffect(() => {
    const sessionExpiree = () => {
      setConnecte(false);
      setCommercant(null);
    };
    window.addEventListener("session-expiree", sessionExpiree);
    return () => window.removeEventListener("session-expiree", sessionExpiree);
  }, []);

  const connexion = useCallback(async (email, motDePasse) => {
    const { data } = await api.post("/api/auth/connexion/", {
      email: email.trim().toLowerCase(),
      mot_de_passe: motDePasse,
    });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    localStorage.setItem("commercant", JSON.stringify(data.commercant));
    setCommercant(data.commercant);
    setConnecte(true);
  }, []);

  const inscription = useCallback(async (email, telephone, motDePasse, nomBoutique, accepteConditions) => {
    // L'API d'inscription ne renvoie pas de JWT : on connecte ensuite le compte.
    await api.post("/api/auth/inscription/", {
      email: email.trim().toLowerCase(),
      telephone,
      nom_boutique: nomBoutique,
      mot_de_passe: motDePasse,
      accepte_conditions: accepteConditions,
    });
    await connexion(email, motDePasse);
  }, [connexion]);

  const deconnexion = useCallback(() => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("commercant");
    setConnecte(false);
    setCommercant(null);
  }, []);

  const valeur = useMemo(
    () => ({ connecte, commercant, connexion, inscription, deconnexion }),
    [connecte, commercant, connexion, inscription, deconnexion],
  );
  return <AuthContext.Provider value={valeur}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
