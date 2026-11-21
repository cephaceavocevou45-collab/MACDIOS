import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { messageErreur } from "../api";
import { branding } from "../config/branding";
import Button from "../composants/Button";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import TelephoneInternational, { telephoneInternationalValide } from "../composants/TelephoneInternational";
import { useToast } from "../composants/ToastProvider";
import { useAuth } from "../contexte/AuthContext";
import { SelecteurLangue, useLangue, TexteLocalise, traduire } from "../contexte/LangueContext";

function AuthAside() {
  return <aside className="auth-aside"><Link to="/" className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</Link><div className="auth-aside-copy"><span className="eyebrow">{<TexteLocalise phrase={"Commencez simplement"} />}</span><h1>{<TexteLocalise phrase={"Un meilleur suivi, dès le premier jour."} />}</h1><p>{<TexteLocalise phrase={"Créez votre espace et rassemblez les informations utiles à la gestion de votre boutique."} />}</p><div className="auth-benefits"><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Inscription avec votre numéro de téléphone"} />}</span><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Interface pensée pour le mobile"} />}</span><span><Icon name="check" size={17}/>{' '}{<TexteLocalise phrase={"Vos produits et vos clients au même endroit"} />}</span></div></div></aside>;
}

export default function Inscription() {
  const { connecte, inscription } = useAuth();
  const { langue } = useLangue();
  const [nomBoutique, setNomBoutique] = useState("");
  const [telephone, setTelephone] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [confirmationMotDePasse, setConfirmationMotDePasse] = useState("");
  const [accepteConditions, setAccepteConditions] = useState(false);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const notifier = useToast();
  const navigate = useNavigate();
  const telephoneValide = telephoneInternationalValide(telephone);
  if (connecte) return <Navigate to="/tableau-de-bord" replace/>;

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setChargement(true);
    if (motDePasse !== confirmationMotDePasse) { setErreur("Les mots de passe ne correspondent pas."); setChargement(false); return; }
    if (!telephone || !telephoneValide) { setErreur("Saisissez un numéro de téléphone valide avec son indicatif international."); setChargement(false); return; }
    if (motDePasse.length < 8) { setErreur("Le mot de passe doit contenir au moins 8 caractères."); setChargement(false); return; }
    try { await inscription(telephone, motDePasse, confirmationMotDePasse, nomBoutique.trim(), accepteConditions); notifier("Votre compte est prêt."); navigate("/tableau-de-bord", {replace: true}); }
    catch (error) { const texte=messageErreur(error); setErreur(texte); notifier(texte,"error"); }
    finally { setChargement(false); }
  }

  return <main className="auth-screen"><AuthAside/><section className="auth-form-side"><div className="auth-form-box"><div className="auth-locale"><SelecteurLangue compact/></div>
    <Link to="/" className="auth-back">{<TexteLocalise phrase={"← Retour à l’accueil"} />}</Link>
    <span className="form-eyebrow">{<TexteLocalise phrase={"Votre espace professionnel"} />}</span><h2>{<TexteLocalise phrase={"Créer mon compte"} />}</h2><p>{<TexteLocalise phrase={"Renseignez ces informations pour démarrer votre boutique."} />}</p>
    {erreur && <div className="alert-box" role="alert">{traduire(erreur, langue)}</div>}
    <form className="auth-form" onSubmit={envoyer}>
      <Input label="Nom de la boutique" autoComplete="organization" placeholder={traduire("Ex. Chez Aïcha")} required value={nomBoutique} onChange={(event) => setNomBoutique(event.target.value)}/>
      <TelephoneInternational label="Numéro de téléphone" value={telephone} onChange={setTelephone} invalid={Boolean(telephone) && !telephoneValide} hint="Obligatoire · ce numéro servira à vous connecter." langue={langue} required/>
      <Input label="Mot de passe" type="password" autoComplete="new-password" minLength={8} maxLength={128} placeholder={traduire("8 caractères minimum")} hint="Choisissez une phrase facile à retenir d’au moins 8 caractères." required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/>
      <Input label="Confirmer le mot de passe" type="password" autoComplete="new-password" minLength={8} maxLength={128} placeholder={traduire("Répétez le mot de passe")} required value={confirmationMotDePasse} aria-invalid={Boolean(confirmationMotDePasse) && confirmationMotDePasse !== motDePasse} onChange={(event) => setConfirmationMotDePasse(event.target.value)}/>
      {confirmationMotDePasse && confirmationMotDePasse !== motDePasse && <small className="field-hint text-red-700" role="status">{traduire("Les mots de passe ne correspondent pas.", langue)}</small>}
      <label className="flex items-start gap-3 text-sm leading-6 text-ink-muted"><input className="mt-1 h-5 w-5 shrink-0 accent-brand" type="checkbox" required checked={accepteConditions} onChange={(event) => setAccepteConditions(event.target.checked)}/><span>{<TexteLocalise phrase={"J'accepte les"} />}{' '}<Link className="font-semibold text-brand underline" to="/conditions">{<TexteLocalise phrase={"conditions d'utilisation"} />}</Link>{' '}{<TexteLocalise phrase={"et la"} />}{' '}<Link className="font-semibold text-brand underline" to="/confidentialite">{<TexteLocalise phrase={"politique de confidentialité"} />}</Link>{' '}{<TexteLocalise phrase={"(modèles à faire valider par un juriste)."} />}</span></label>
      <Button type="submit" className="w-full" disabled={chargement}>{chargement ? "Création du compte…" : "Créer mon compte"}<Icon name="arrow" size={17}/></Button>
    </form>
    <p className="auth-switch">{<TexteLocalise phrase={"Vous avez déjà un compte ?"} />}{' '}<Link to="/connexion">{<TexteLocalise phrase={"Se connecter"} />}</Link></p>
  </div></section></main>;
}
