import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { api, messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Input from "../composants/Input";
import { useAuth } from "../contexte/AuthContext";
import { TexteLocalise } from "../contexte/LangueContext";

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

  return <main className="auth-screen"><aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">{<TexteLocalise phrase={"Sécurité du compte"} />}</span><h1>{<TexteLocalise phrase={"Choisissez un nouveau mot de passe."} />}</h1><p>{<TexteLocalise phrase={"Le lien ne fonctionne qu’une fois et expire après 15 minutes."} />}</p></div></aside>
    <section className="auth-form-side"><div className="auth-form-box"><Link to="/connexion" className="auth-back">{<TexteLocalise phrase={"← Retour à la connexion"} />}</Link><span className="form-eyebrow">{<TexteLocalise phrase={"Nouveau mot de passe"} />}</span><h2>{<TexteLocalise phrase={"Mettre à jour l’accès"} />}</h2><p>{<TexteLocalise phrase={"Choisissez un mot de passe d’au moins 8 caractères."} />}</p>
      {erreur && <div className="alert-box" role="alert">{erreur}</div>}{termine ? <div className="success-box" role="status">{<TexteLocalise phrase={"Votre mot de passe a été modifié."} />}{' '}<Link to="/connexion">{<TexteLocalise phrase={"Connectez-vous."} />}</Link></div> : <form className="auth-form" onSubmit={envoyer}><Input label="Nouveau mot de passe" type="password" autoComplete="new-password" minLength={8} required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/><Input label="Confirmer le mot de passe" type="password" autoComplete="new-password" minLength={8} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)}/><Button type="submit" className="w-full" disabled={chargement}>{chargement ? "Mise à jour…" : "Enregistrer le nouveau mot de passe"}</Button></form>}
    </div></section></main>;
}
