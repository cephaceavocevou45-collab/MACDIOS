import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Input from "../composants/Input";
import { useAuth } from "../contexte/AuthContext";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

export default function MotDePasseOublie() {
  const { connecte } = useAuth();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const valide = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setMessage(""); setChargement(true);
    try {
      const { data } = await api.post("/api/auth/mot-de-passe/oublie/", { email: email.trim().toLowerCase() });
      setMessage(data.detail);
    } catch (error) { setErreur(messageErreur(error)); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">{<TexteLocalise phrase={"Récupération du compte"} />}</span><h1>{<TexteLocalise phrase={"Retrouvez l’accès à votre boutique."} />}</h1><p>{<TexteLocalise phrase={"Un lien temporaire peut être demandé avec l’adresse email associée à votre compte."} />}</p></div></aside>
    <section className="auth-form-side"><div className="auth-form-box"><Link to="/connexion" className="auth-back">{<TexteLocalise phrase={"← Retour à la connexion"} />}</Link><span className="form-eyebrow">{<TexteLocalise phrase={"Aide à la connexion"} />}</span><h2>{<TexteLocalise phrase={"Mot de passe oublié"} />}</h2><p>{<TexteLocalise phrase={"Saisissez l’adresse email utilisée à l’inscription."} />}</p>
      {erreur && <div className="alert-box" role="alert">{erreur}</div>}{message && <div className="success-box" role="status">{message}</div>}
      <form className="auth-form" onSubmit={envoyer}><Input label="Adresse email" type="email" inputMode="email" autoComplete="email" maxLength={254} placeholder={traduire("Ex. vous@exemple.com")} required value={email} onChange={(event) => setEmail(event.target.value)}/><Button type="submit" className="w-full" disabled={chargement || !valide}>{chargement ? "Demande en cours…" : "Recevoir un lien par email"}</Button></form>
      <p className="field-hint mt-4">{<TexteLocalise phrase={"Le lien expire après 15 minutes et ne peut être utilisé qu’une fois."} />}</p>
    </div></section></main>;
}
