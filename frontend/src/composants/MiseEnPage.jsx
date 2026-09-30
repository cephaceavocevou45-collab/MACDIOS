import { Link, NavLink, Outlet } from "react-router-dom";
import { branding } from "../config/branding";
import Icon from "./Icon";
import NavigationBas from "./NavigationBas";
import { useAuth } from "../contexte/AuthContext";
import AlerteAbonnement from "./AlerteAbonnement";
import FooterApplication from "./FooterApplication";

const liens = [
  { to: "/tableau-de-bord", label: "Vue d’ensemble", icon: "home", end: true },
  { to: "/ventes/nouvelle", label: "Nouvelle vente", icon: "cart" },
  { to: "/produits", label: "Produits", icon: "box" },
  { to: "/clients", label: "Clients", icon: "users" },
  { to: "/ventes/historique", label: "Historique", icon: "chart" },
  { to: "/abonnement", label: "Abonnement", icon: "subscription" },
  { to: "/activite", label: "Historique d'activité", icon: "clock" },
  { to: "/compte/donnees", label: "Mes données", icon: "shield" },
];

function LiensNavigation({ className = "" }) {
  return <nav className={className}>{liens.map((lien) => <NavLink key={lien.to} to={lien.to} end={lien.end} className={({isActive}) => `sidebar-link ${isActive ? "active" : ""}`}><Icon name={lien.icon}/>{lien.label}</NavLink>)}</nav>;
}

export function Sidebar() {
  const { commercant, deconnexion } = useAuth();
  return (
    <aside className="app-sidebar">
      <a href="/tableau-de-bord" className="sidebar-brand"><span className="brand-mark">{branding.logoMark}</span><span><strong>{branding.appName}</strong><small className="block text-xs font-normal text-ink-muted">Espace commerçant</small></span></a>
      <LiensNavigation className="sidebar-nav"/>
      <div className="sidebar-bottom">
        <p className="truncate px-3 pb-2 text-xs text-ink-muted">{commercant?.nom_boutique || "Ma boutique"}</p>
        <button className="sidebar-link w-full border-0 bg-transparent text-left" onClick={deconnexion}><Icon name="logout"/>Déconnexion</button>
      </div>
    </aside>
  );
}

export default function MiseEnPage() {
  const { commercant, deconnexion } = useAuth();
  return (
    <div className="app-workspace">
      <Sidebar/>
      <div className="workspace-main">
        <header className="workspace-topbar"><div><strong>{commercant?.nom_boutique || "Ma boutique"}</strong><span className="ml-2 text-sm text-ink-muted">· Votre espace de gestion</span></div><button className="btn-ghost" onClick={deconnexion}><Icon name="logout" size={17}/>Quitter</button></header>
        <header className="workspace-mobile-header"><a className="brand-lockup" href="/tableau-de-bord"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</a><div className="flex items-center gap-2"><Link to="/activite" className="icon-button" aria-label="Historique d'activité" title="Historique d'activité"><Icon name="clock"/></Link><Link to="/compte/donnees" className="icon-button" aria-label="Mes données" title="Mes données"><Icon name="shield"/></Link><Link to="/abonnement" className="icon-button" aria-label="Mon abonnement" title="Mon abonnement"><Icon name="subscription"/></Link><button className="icon-button" aria-label="Déconnexion" onClick={deconnexion}><Icon name="logout"/></button></div></header>
        <AlerteAbonnement/>
        <main className="workspace-content"><Outlet/></main>
        <FooterApplication/>
      </div>
      <NavigationBas/>
    </div>
  );
}
