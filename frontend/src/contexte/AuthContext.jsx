import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, initialiserCSRF, viderRequetesIdempotentesEnAttente } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [connecte, setConnecte] = useState(false);
  const [initialisation, setInitialisation] = useState(true);
  const [commercant, setCommercant] = useState(() => {
    try { return JSON.parse(localStorage.getItem("commercant") || "null"); }
    catch { return null; }
  });

  useEffect(() => {
    let actif = true;
    const demarrer = async () => {
      try {
        await initialiserCSRF();
        const { data } = await api.get("/api/auth/session/");
        if (actif && data.commercant) {
          setCommercant(data.commercant);
          localStorage.setItem("commercant", JSON.stringify(data.commercant));
          setConnecte(true);
        } else if (actif) {
          setCommercant(null);
          localStorage.removeItem("commercant");
        }
      } catch {
        if (actif) {
          setCommercant(null);
          localStorage.removeItem("commercant");
        }
      } finally { if (actif) setInitialisation(false); }
    };
    demarrer();
    const sessionExpiree = () => { setConnecte(false); setCommercant(null); };
    window.addEventListener("session-expiree", sessionExpiree);
    return () => { actif = false; window.removeEventListener("session-expiree", sessionExpiree); };
  }, []);

  const connexion = useCallback(async (identifiant, motDePasse, mode = "telephone") => {
    viderRequetesIdempotentesEnAttente();
    await initialiserCSRF();
    const cle = mode === "email" ? "email" : "telephone";
    const valeurIdentifiant = mode === "email" ? identifiant.trim().toLowerCase() : identifiant.trim();
    const { data } = await api.post("/api/auth/connexion/", { [cle]: valeurIdentifiant, mot_de_passe: motDePasse });
    localStorage.setItem("commercant", JSON.stringify(data.commercant));
    setCommercant(data.commercant);
    setConnecte(true);
  }, []);

  const inscription = useCallback(async (telephone, motDePasse, confirmationMotDePasse, nomBoutique, accepteConditions) => {
    await initialiserCSRF();
    await api.post("/api/auth/inscription/", {
      telephone, nom_boutique: nomBoutique, mot_de_passe: motDePasse,
      confirmation_mot_de_passe: confirmationMotDePasse, accepte_conditions: accepteConditions,
    });
    await connexion(telephone, motDePasse, "telephone");
  }, [connexion]);

  const deconnexion = useCallback(async () => {
    viderRequetesIdempotentesEnAttente();
    try { await api.post("/api/auth/deconnexion/", {}); } finally {
      localStorage.removeItem("commercant");
      setConnecte(false);
      setCommercant(null);
    }
  }, []);

  const valeur = useMemo(
    () => ({ connecte, initialisation, commercant, connexion, inscription, deconnexion }),
    [connecte, initialisation, commercant, connexion, inscription, deconnexion],
  );
  return <AuthContext.Provider value={valeur}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
