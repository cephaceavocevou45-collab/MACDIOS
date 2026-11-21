import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Input from "../composants/Input";
import TelephoneInternational, { telephoneInternationalValide } from "../composants/TelephoneInternational";
import { useAuth } from "../contexte/AuthContext";
import { TexteLocalise, traduire, useLangue } from "../contexte/LangueContext";

export default function MotDePasseOublie() {
  const { connecte } = useAuth();
  const { langue } = useLangue();
  const [identifiant, setIdentifiant] = useState("");
  const [modeEmail, setModeEmail] = useState(false);
  const [message, setMessage] = useState("");
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const valide = modeEmail
    ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifiant.trim())
    : Boolean(identifiant) && telephoneInternationalValide(identifiant);
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setMessage(""); setChargement(true);
    try {
      const identifiantNormalise = modeEmail ? { email: identifiant.trim().toLowerCase() } : { telephone: identifiant.trim() };
      const { data } = await api.post("/api/auth/mot-de-passe/oublie/", identifiantNormalise);
      setMessage(data.detail);
    } catch (error) { setErreur(messageErreur(error)); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">{<TexteLocalise phrase={"Récupération du compte"} />}</span><h1>{<TexteLocalise phrase={"Retrouvez l’accès à votre boutique."} />}</h1><p>{<TexteLocalise phrase={"Un lien temporaire sera envoyé au numéro associé à votre compte."} />}</p></div></aside>
    <section className="auth-form-side"><div className="auth-form-box"><Link to="/connexion" className="auth-back">{<TexteLocalise phrase={"← Retour à la connexion"} />}</Link><span className="form-eyebrow">{<TexteLocalise phrase={"Aide à la connexion"} />}</span><h2>{<TexteLocalise phrase={"Mot de passe oublié"} />}</h2><p>{<TexteLocalise phrase={"Saisissez le numéro utilisé à l’inscription."} />}</p>
      {erreur && <div className="alert-box" role="alert">{erreur}</div>}{message && <div className="success-box" role="status">{message}</div>}
      <form className="auth-form" onSubmit={envoyer}>{modeEmail
        ? <Input label="Adresse email de l’ancien compte" type="email" inputMode="email" autoComplete="email" maxLength={254} placeholder={traduire("Ex. vous@exemple.com")} required value={identifiant} onChange={(event) => setIdentifiant(event.target.value)}/>
        : <TelephoneInternational label="Numéro de téléphone" value={identifiant} onChange={setIdentifiant} invalid={Boolean(identifiant) && !valide} hint="Utilisez le numéro lié à votre compte." langue={langue} required/>}
        <Button type="submit" className="w-full" disabled={chargement || !valide}>{chargement ? "Demande en cours…" : modeEmail ? "Recevoir un lien par email" : "Recevoir un lien par SMS"}</Button></form>
      <p className="auth-switch"><button type="button" className="text-brand underline" onClick={() => { setModeEmail((actuel) => !actuel); setIdentifiant(""); setMessage(""); setErreur(""); }}>{modeEmail ? "Utiliser un numéro de téléphone" : "Ancien compte sans numéro ? Utiliser l’email"}</button></p>
      <p className="field-hint mt-4">{<TexteLocalise phrase={"Le lien expire après 15 minutes et ne peut être utilisé qu’une fois."} />}</p>
    </div></section></main>;
}
