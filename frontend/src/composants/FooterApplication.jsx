import { Link, useLocation } from "react-router-dom";
import { branding } from "../config/branding";
import { SelecteurLangue, TexteLocalise, traduire } from "../contexte/LangueContext";

const nomsReseaux = {
  facebook: "Facebook",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
  linkedin: "LinkedIn",
  tiktok: "TikTok",
  youtube: "YouTube",
};

function IcôneRéseau({ name }) {
  const formes = {
    facebook: <path d="M14 21v-8h3l.5-3H14V8c0-.9.3-1.5 1.6-1.5H18V3.8c-.7-.1-1.6-.2-2.7-.2-2.7 0-4.5 1.6-4.5 4.6V10H8v3h2.8v8Z" fill="currentColor" stroke="none"/>,
    instagram: <><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17.6 6.5h.01"/></>,
    whatsapp: <><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M9 8.5c.5 2 2 3.5 4.5 4.5l1-1 2 1-.5 2c-4 .7-8.8-4-8-8l2-.5 1 2-1 1Z"/></>,
    linkedin: <><path d="M5 9v10M5 5h.01M10 19v-6a3 3 0 0 1 6 0v6M10 10v9"/><circle cx="5" cy="5" r="1"/></>,
    tiktok: <><path d="M14 4v10a4 4 0 1 1-4-4"/><path d="M14 4c.5 2.2 2.1 3.6 4.5 4"/></>,
    youtube: <><rect x="3" y="5" width="18" height="14" rx="4"/><path d="m10 9 5 3-5 3Z" fill="currentColor" stroke="none"/></>,
  };

  return <svg aria-hidden="true" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{formes[name]}</svg>;
}

export default function FooterApplication({ compact = false }) {
  const { pathname } = useLocation();
  const ancreAccueil = (id) => pathname === "/" ? `#${id}` : `/#${id}`;
  const réseauxConfigurés = Object.entries(branding.socials).filter(([, url]) => Boolean(url?.trim()));

  if (compact) return <footer className="public-footer application-footer-compact" id="contact">
    <div className="public-container application-footer-compact-inner">
      <Link className="brand-lockup brand-light application-footer-brand" to="/" aria-label={branding.appName}><img className="macdios-wordmark" src="/macdios-wordmark.png?v=2" alt={branding.appName} /></Link>
      <nav className="application-footer-links" aria-label={traduire("Liens utiles")}>
        <Link to="/contact" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Contactez-nous"} />}</Link>
        <Link to="/conditions" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Conditions d’utilisation"} />}</Link>
        <Link to="/confidentialite" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Confidentialité"} />}</Link>
      </nav>
      <span className="application-footer-copyright">© {new Date().getFullYear()} {branding.appName}</span>
    </div>
  </footer>;

  return <footer className="public-footer" id="contact">
    <div className="public-container">
      <div className="footer-grid">
        <div className="footer-brand">
          <Link className="brand-lockup brand-light" to="/" aria-label={branding.appName}><img className="macdios-wordmark" src="/macdios-wordmark.png?v=2" alt={branding.appName} /></Link>
          <p>{branding.appDescription}{' '}{<TexteLocalise phrase={"Un outil simple pour mieux suivre les ventes, les produits et les clients."} />}</p>
          {réseauxConfigurés.length > 0 && <div className="social-links">{réseauxConfigurés.map(([réseau, url]) => <a key={réseau} className="social-link" href={url} target="_blank" rel="noreferrer" aria-label={nomsReseaux[réseau]}><IcôneRéseau name={réseau}/></a>)}</div>}
        </div>
        <nav className="footer-column" aria-label={traduire("Solution")}><h3>{<TexteLocalise phrase={"Solution"} />}</h3><a href={ancreAccueil("fonctionnalites")}>{<TexteLocalise phrase={"Fonctionnalités"} />}</a><a href={ancreAccueil("comment-ca-marche")}>{<TexteLocalise phrase={"Comment ça marche"} />}</a><a href={ancreAccueil("tarifs")}>{<TexteLocalise phrase={"Tarifs"} />}</a><Link to="/inscription">{<TexteLocalise phrase={"Créer un compte"} />}</Link></nav>
        <div className="footer-column"><h3>{<TexteLocalise phrase={"Entreprise"} />}</h3><Link to="/contact" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Contactez-nous"} />}</Link><Link to="/connexion">{<TexteLocalise phrase={"Se connecter"} />}</Link><a href={ancreAccueil("faq")}>{<TexteLocalise phrase={"Questions fréquentes"} />}</a></div>
        <nav className="footer-column" aria-label={traduire("Informations légales")}><h3>{<TexteLocalise phrase={"Légal"} />}</h3><Link to="/conditions" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Conditions d’utilisation"} />}</Link><Link to="/confidentialite" state={{ retourVers: pathname }}>{<TexteLocalise phrase={"Confidentialité"} />}</Link></nav>
      </div>
      <div className="footer-bottom"><span>© {new Date().getFullYear()} {branding.appName}{<TexteLocalise phrase={". Tous droits réservés."} />}</span><SelecteurLangue compact/></div>
    </div>
  </footer>;
}
