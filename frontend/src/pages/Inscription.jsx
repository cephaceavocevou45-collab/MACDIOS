import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import { useToast } from "../composants/ToastProvider";
import { useAuth } from "../contexte/AuthContext";

function AuthAside() {
  return <aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">Commencez simplement</span><h1>Un meilleur suivi, dès le premier jour.</h1><p>Créez votre espace et rassemblez les informations utiles à la gestion de votre boutique.</p><div className="auth-benefits"><span><Icon name="check" size={17}/> Inscription avec votre email</span><span><Icon name="check" size={17}/> Interface pensée pour le mobile</span><span><Icon name="check" size={17}/> Vos produits et vos clients au même endroit</span></div></div></aside>;
}

export default function Inscription() {
  const { connecte, inscription } = useAuth();
  const [nomBoutique, setNomBoutique] = useState("");
  const [email, setEmail] = useState("");
  const [telephone, setTelephone] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [accepteConditions, setAccepteConditions] = useState(false);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const notifier = useToast();
  const navigate = useNavigate();
  const emailValide = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const telephoneValide = !telephone || /^\+229[0-9]{8}$/.test(telephone);
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setChargement(true);
    if (!emailValide) { setErreur("Saisissez une adresse email valide."); setChargement(false); return; }
    if (!telephoneValide) { setErreur("Si vous ajoutez un téléphone, utilisez +229 suivi de 8 chiffres, sans espace."); setChargement(false); return; }
    try { await inscription(email, telephone, motDePasse, nomBoutique.trim(), accepteConditions); notifier("Votre compte est prêt."); navigate("/tableau-de-bord", {replace: true}); }
    catch (error) { const texte=messageErreur(error); setErreur(texte); notifier(texte,"error"); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><AuthAside/><section className="auth-form-side"><div className="auth-form-box">
    <Link to="/" className="auth-back">← Retour à l’accueil</Link>
    <span className="form-eyebrow">Votre espace professionnel</span><h2>Créer mon compte</h2><p>Renseignez ces informations pour démarrer votre boutique.</p>
    {erreur && <div className="alert-box" role="alert">{erreur}</div>}
    <form className="auth-form" onSubmit={envoyer}>
      <Input label="Nom de la boutique" autoComplete="organization" placeholder="Ex. Chez Aïcha" required value={nomBoutique} onChange={(event) => setNomBoutique(event.target.value)}/>
      <Input label="Adresse email" type="email" autoComplete="email" inputMode="email" maxLength={254} placeholder="Ex. vous@exemple.com" required value={email} onChange={(event) => setEmail(event.target.value)}/>
      <Input label="Téléphone de contact (facultatif)" type="tel" autoComplete="tel" inputMode="tel" maxLength={12} pattern="\+229[0-9]{8}" placeholder="Ex. +22961020304" hint={telephone && !telephoneValide ? "Format attendu : +229 suivi de 8 chiffres, sans espace." : "Utile pour les rappels SMS. Format : +229 suivi de 8 chiffres."} aria-invalid={Boolean(telephone) && !telephoneValide} value={telephone} onChange={(event) => setTelephone(event.target.value)}/>
      <Input label="Mot de passe" type="password" autoComplete="new-password" minLength={12} placeholder="12 caractères minimum" required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/>
      <label className="flex items-start gap-3 text-sm leading-6 text-ink-muted"><input className="mt-1 h-5 w-5 shrink-0 accent-brand" type="checkbox" required checked={accepteConditions} onChange={(event) => setAccepteConditions(event.target.checked)}/><span>J&apos;accepte les <Link className="font-semibold text-brand underline" to="/conditions">conditions d&apos;utilisation</Link> et la <Link className="font-semibold text-brand underline" to="/confidentialite">politique de confidentialité</Link> (modèles à faire valider par un juriste).</span></label>
      <Button type="submit" className="w-full" disabled={chargement}>{chargement ? "Création du compte…" : "Créer mon compte"}<Icon name="arrow" size={17}/></Button>
    </form>
    <p className="auth-switch">Vous avez déjà un compte ? <Link to="/connexion">Se connecter</Link></p>
  </div></section></main>;
}
