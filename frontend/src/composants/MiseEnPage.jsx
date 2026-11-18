import { Link, NavLink, Outlet } from "react-router-dom";
import { branding } from "../config/branding";
import Icon from "./Icon";
import NavigationBas from "./NavigationBas";
import { useAuth } from "../contexte/AuthContext";
import AlerteAbonnement from "./AlerteAbonnement";
import FooterApplication from "./FooterApplication";
import AvatarProfil from "./AvatarProfil";
import { SelecteurLangue, traduire, useLangue, TexteLocalise } from "../contexte/LangueContext";

const liens = [
  { to: "/tableau-de-bord", label: "Vue d'ensemble", icon: "home", end: true },
  { to: "/ventes/nouvelle", label: "Nouvelle vente", icon: "cart" },
  { to: "/produits", label: "Produits", icon: "box" },
  { to: "/fournisseurs", label: "Fournisseurs", icon: "users" },
  { to: "/approvisionnements", label: "Réceptions", icon: "box" },
  { to: "/mouvements-stock", label: "Mouvements de stock", icon: "clock" },
  { to: "/clients", label: "Clients", icon: "users" },
  { to: "/ventes/historique", label: "Historique", icon: "chart" },
  { to: "/abonnement", label: "Abonnement", icon: "subscription" },
  { to: "/activite", label: "Historique d'activité", icon: "clock" },
  { to: "/compte/donnees", label: "Mes données", icon: "shield" },
  { to: "/profil", label: "Mon profil", icon: "users" },
];

function LiensNavigation({ className = "" }) {
  const { langue } = useLangue();
  const navigation = [...liens, { to: "/parametres", label: "Paramètres", icon: "settings" }];
  return <nav className={className}>{navigation.map((lien) => <NavLink key={lien.to} to={lien.to} end={lien.end} className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}><Icon name={lien.icon}/>{traduire(lien.label, langue)}</NavLink>)}</nav>;
}

export function Sidebar() {
  const { commercant, deconnexion } = useAuth();
  return (
    <aside className="app-sidebar">
      <a href="/tableau-de-bord" className="sidebar-brand"><span className="brand-mark">{branding.logoMark}</span><span><strong>{branding.appName}</strong><small className="block text-xs font-normal text-ink-muted">{<TexteLocalise phrase={"Espace commerçant"} />}</small></span></a>
      <LiensNavigation className="sidebar-nav"/>
      <div className="sidebar-bottom">
        <p className="truncate px-3 pb-2 text-xs text-ink-muted">{commercant?.nom_boutique || "Ma boutique"}</p>
        <button className="sidebar-link w-full border-0 bg-transparent text-left" onClick={deconnexion}><Icon name="logout"/>{<TexteLocalise phrase={"Déconnexion"} />}</button>
      </div>
    </aside>
  );
}

export default function MiseEnPage() {
  const { commercant, deconnexion } = useAuth();
  const { langue } = useLangue();
  return (
    <div className="app-workspace">
      <Sidebar/>
      <div className="workspace-main">
        <header className="workspace-topbar"><div><strong>{commercant?.nom_boutique || "Ma boutique"}</strong><span className="ml-2 text-sm text-ink-muted">· {traduire("Votre espace de gestion", langue)}</span></div><div className="flex items-center gap-3"><SelecteurLangue compact/><AvatarProfil/><button className="btn-ghost" onClick={deconnexion}><Icon name="logout" size={17}/>{traduire("Quitter", langue)}</button></div></header>
        <header className="workspace-mobile-header"><a className="brand-lockup" href="/tableau-de-bord"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</a><div className="flex items-center gap-2"><SelecteurLangue compact/><Link to="/parametres" className="icon-button" aria-label={traduire("Paramètres")} title={traduire("Paramètres")}><Icon name="settings"/></Link><AvatarProfil compact/><Link to="/activite" className="icon-button" aria-label={traduire("Historique d'activité")} title={traduire("Historique d'activité")}><Icon name="clock"/></Link><button className="icon-button" aria-label={traduire("Déconnexion")} onClick={deconnexion}><Icon name="logout"/></button></div></header>
        <AlerteAbonnement/>
        <main className="workspace-content"><Outlet/></main>
        <FooterApplication compact/>
      </div>
      <NavigationBas/>
    </div>
  );
}
