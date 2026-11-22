import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { traduire } from "../contexte/LangueContext";
import { branding, nomBoutiqueAffiche } from "../config/branding";

export default function AvatarProfil({ to = "/profil", compact = false }) {
  const [profil, setProfil] = useState(null);
  const charger = useCallback(async () => {
    try {
      const { data } = await api.get("/api/profil/");
      setProfil(data);
    } catch {
      setProfil(null);
    }
  }, []);

  useEffect(() => {
    charger();
    window.addEventListener("profil-modifie", charger);
    return () => window.removeEventListener("profil-modifie", charger);
  }, [charger]);

  return <Link
    to={to}
    aria-label={traduire("Ouvrir mon profil")}
    title={nomBoutiqueAffiche(profil?.nom_affiche) || "Mon profil"}
    className={`inline-flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-brand/20 bg-brand/10 font-bold text-brand ${compact ? "h-9 w-9" : ""}`}
  >
    {profil?.logo_url
      ? <img src={profil.logo_url} alt={traduire("Logo du profil")} className="h-full w-full object-cover" />
      : <img src="/app-icon-192.png?v=2" alt={branding.appName} className="h-full w-full object-cover" />}
  </Link>;
}
