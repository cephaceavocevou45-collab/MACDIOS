import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { aPermission, useAdminAuth } from "./AdminAuthContext";
import FooterApplication from "../composants/FooterApplication";
import AvatarProfil from "../composants/AvatarProfil";
import { branding } from "../config/branding";
import { SelecteurLangue, TexteLocalise, traduire, useLangue } from "../contexte/LangueContext";


const liens = [
  ["/admin/statistiques", "Vue d’ensemble", "▦", "voir_statistiques"],
  ["/admin/utilisateurs", "Commerçants", "♙", "voir_utilisateurs"],
  ["/admin/paiements", "Paiements", "▤", "valider_paiements"],
  ["/admin/audit", "Journal d’audit", "◷", "voir_audit"],
  ["/admin/sous-admins", "Sous-admins", "♧", "super_admin"],
  ["/admin/offre-essai", "Offre gratuite", "◷", "super_admin"],
  ["/admin/maintenance", "Maintenance", "⚙", "super_admin"],
];

export default function AdminLayout() {
  const { administrateur, deconnexion } = useAdminAuth();
  const { langue } = useLangue();
  const navigate = useNavigate();
  const visibles = liens.filter(([, , , permission]) => permission === "super_admin" ? administrateur?.super_admin : aPermission(administrateur, permission));
  const quitter = () => { deconnexion(); navigate("/admin/connexion", { replace: true }); };

  return <div className="admin-shell">
    <aside className="admin-sidebar">
      <div className="admin-brand"><span className="admin-brand-mark">{branding.logoMark}</span><span>{branding.appName}<small>{<TexteLocalise phrase={"BACK-OFFICE"} />}</small></span></div>
      <div className="admin-menu-label">{<TexteLocalise phrase={"GESTION"} />}</div>
      <nav className="admin-nav">{visibles.map(([to, label, icon]) => <NavLink key={to} to={to} end={to === "/admin"} className={({ isActive }) => `admin-nav-link${isActive ? " active" : ""}`}><span className="admin-nav-icon">{icon}</span>{traduire(label, langue)}</NavLink>)}</nav>
      <div className="admin-sidebar-footer"><div className="admin-profile"><AvatarProfil to="/admin/profil" compact/><div><strong>{administrateur?.nom || "Administrateur"}</strong><small>{administrateur?.super_admin ? "Super admin" : "Sous-admin"}</small></div></div><button onClick={quitter} className="admin-logout">{<TexteLocalise phrase={"Déconnexion"} />}</button></div>
    </aside>
    <main className="admin-main"><div className="admin-topbar"><span>{<TexteLocalise phrase={"Plateforme /"} />}{' '}<strong>{<TexteLocalise phrase={"Back-office"} />}</strong></span><SelecteurLangue compact/><AvatarProfil to="/admin/profil"/><span className="admin-secure">{<TexteLocalise phrase={"● Session sécurisée"} />}</span></div><section className="admin-content"><Outlet/></section><FooterApplication compact/></main>
  </div>;
}
