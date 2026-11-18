import { NavLink } from "react-router-dom";
import Icon from "./Icon";
import { traduire } from "../contexte/LangueContext";

const liens = [
  { to: "/tableau-de-bord", label: "Accueil", icon: "home", end: true },
  { to: "/ventes/nouvelle", label: "Vendre", icon: "cart" },
  { to: "/produits", label: "Produits", icon: "box" },
  { to: "/clients", label: "Clients", icon: "users" },
];

export default function NavigationBas() {
  return <nav className="mobile-nav" aria-label={traduire("Navigation principale")}>{liens.map((lien) => <NavLink key={lien.to} to={lien.to} end={lien.end} className={({isActive}) => isActive ? "active" : ""}><Icon name={lien.icon}/>{lien.label}</NavLink>)}</nav>;
}
