import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import { useToast } from "../composants/ToastProvider";
import { useAuth } from "../contexte/AuthContext";
import { SelecteurLangue, TexteLocalise, traduire } from "../contexte/LangueContext";

function AuthAside() {
  return <aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">{<TexteLocalise phrase={"Votre commerce, en confiance"} />}</span><h1>{<TexteLocalise phrase={"Tout votre commerce à portée de main."} />}</h1><p>{<TexteLocalise phrase={"Gardez vos ventes, votre stock et vos comptes clients bien organisés, même quand la journée s’accélère."} />}</p><div className="auth-benefits"><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Simple à utiliser sur téléphone"} />}</span><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Vos données restent dans votre espace"} />}</span><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Un aperçu clair de votre activité"} />}</span></div></div></aside>;
}

export default function Connexion() {
  const { connecte, connexion } = useAuth();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const notifier = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const emailValide = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setChargement(true);
    if (!emailValide) { setErreur("Saisissez une adresse email valide."); setChargement(false); return; }
    try { await connexion(email, motDePasse); notifier("Connexion réussie."); navigate(location.state?.depuis || "/tableau-de-bord", {replace: true}); }
    catch (error) { const texte=messageErreur(error); setErreur(texte); notifier(texte,"error"); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><AuthAside/><section className="auth-form-side"><div className="auth-form-box"><div className="auth-locale"><SelecteurLangue compact/></div>
    <Link to="/" className="auth-back">{<TexteLocalise phrase={"← Retour à l’accueil"} />}</Link>
    <span className="form-eyebrow">{<TexteLocalise phrase={"Ravi de vous revoir"} />}</span><h2>{<TexteLocalise phrase={"Connexion"} />}</h2><p>{<TexteLocalise phrase={"Connectez-vous pour retrouver votre espace commerçant."} />}</p>
    {erreur && <div className="alert-box" role="alert">{traduire(erreur)}</div>}
    <form className="auth-form" onSubmit={envoyer}>
      <Input label="Adresse email" type="email" autoComplete="email" inputMode="email" maxLength={254} placeholder={traduire("Ex. vous@exemple.com")} aria-invalid={Boolean(email) && !emailValide} required value={email} onChange={(event) => setEmail(event.target.value)}/>
      <Input label="Mot de passe" type="password" autoComplete="current-password" placeholder={traduire("Votre mot de passe")} required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/>
      <Button type="submit" className="w-full" disabled={chargement}>{chargement ? "Connexion…" : "Se connecter"}<Icon name="arrow" size={17}/></Button>
    </form>
    <p className="auth-switch"><Link to="/mot-de-passe-oublie">{<TexteLocalise phrase={"Mot de passe oublié ?"} />}</Link></p>
    <p className="auth-switch">{<TexteLocalise phrase={"Vous débutez ?"} />}{' '}<Link to="/inscription">{<TexteLocalise phrase={"Créer mon compte"} />}</Link></p>
  </div></section></main>;
}
