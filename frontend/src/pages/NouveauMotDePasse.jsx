import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { api, messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Input from "../composants/Input";
import { useAuth } from "../contexte/AuthContext";

export default function NouveauMotDePasse() {
  const { connecte } = useAuth();
  const [parametres] = useSearchParams();
  const uid = parametres.get("uid") || "";
  const token = parametres.get("token") || "";
  const [motDePasse, setMotDePasse] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState("");
  const [termine, setTermine] = useState(false);
  const [chargement, setChargement] = useState(false);
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur("");
    if (!uid || !token) { setErreur("Le lien est incomplet. Demandez un nouveau lien."); return; }
    if (motDePasse !== confirmation) { setErreur("Les deux mots de passe ne correspondent pas."); return; }
    setChargement(true);
    try {
      await api.post("/api/auth/mot-de-passe/reinitialiser/", {
        uid, token, nouveau_mot_de_passe: motDePasse,
      });
      setTermine(true);
    } catch (error) { setErreur(messageErreur(error)); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">Sécurité du compte</span><h1>Choisissez un nouveau mot de passe.</h1><p>Le lien ne fonctionne qu’une fois et expire après 15 minutes.</p></div></aside>
    <section className="auth-form-side"><div className="auth-form-box"><Link to="/connexion" className="auth-back">← Retour à la connexion</Link><span className="form-eyebrow">Nouveau mot de passe</span><h2>Mettre à jour l’accès</h2><p>Choisissez un mot de passe d’au moins 12 caractères.</p>
      {erreur && <div className="alert-box" role="alert">{erreur}</div>}{termine ? <div className="success-box" role="status">Votre mot de passe a été modifié. <Link to="/connexion">Connectez-vous.</Link></div> : <form className="auth-form" onSubmit={envoyer}><Input label="Nouveau mot de passe" type="password" autoComplete="new-password" minLength={12} required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/><Input label="Confirmer le mot de passe" type="password" autoComplete="new-password" minLength={12} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)}/><Button type="submit" className="w-full" disabled={chargement}>{chargement ? "Mise à jour…" : "Enregistrer le nouveau mot de passe"}</Button></form>}
    </div></section></main>;
}
