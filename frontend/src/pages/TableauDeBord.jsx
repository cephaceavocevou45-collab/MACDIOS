import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";

const jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const statistiques = [
  { cle: "ventes_jour", titre: "Ventes aujourd’hui", icon: "cart", couleur: "#eaf5ef", encre: "#0c765c" },
  { cle: "ventes_semaine", titre: "Cette semaine", icon: "chart", couleur: "#fff2df", encre: "#ac7016" },
  { cle: "ventes_mois", titre: "Ce mois", icon: "wallet", couleur: "#edf0fa", encre: "#5868a7" },
  { cle: "total_dettes_en_cours", titre: "Dettes en cours", icon: "users", couleur: "#fbeeed", encre: "#a7463d" },
];

function GraphiqueVentes({ ventes }) {
  const totaux = Array(7).fill(0);
  ventes.forEach((vente) => {
    const date = new Date(vente.date);
    const jour = (date.getDay() + 6) % 7;
    totaux[jour] += Number(vente.total || 0);
  });
  const max = Math.max(...totaux, 1);
  const x0 = 30, largeur = 470, haut = 145, baseY = 162;
  const barWidth = 31, espace = largeur / 7;
  return <div className="chart-wrap"><svg viewBox="0 0 530 195" role="img" aria-label="Montant des ventes par jour cette semaine">
    {[25, 70, 115, 160].map((y) => <line key={y} className="chart-grid-line" x1="25" x2="510" y1={y} y2={y}/>)}
    {totaux.map((valeur, index) => {
      const hauteur = Math.max((valeur / max) * haut, valeur ? 9 : 3);
      const x = x0 + index * espace + (espace - barWidth) / 2;
      return <g key={jours[index]}><rect className="chart-bar" x={x} y={baseY - hauteur} width={barWidth} height={hauteur} rx="8" opacity={valeur ? 1 : .18}/><text className="chart-label" x={x + barWidth / 2} y="185" textAnchor="middle">{jours[index]}</text></g>;
    })}
  </svg></div>;
}

export default function TableauDeBord() {
  const [donnees, setDonnees] = useState(null);
  const [ventesSemaine, setVentesSemaine] = useState([]);
  const [erreur, setErreur] = useState("");
  const [erreurGraphique, setErreurGraphique] = useState("");
  const notifier = useToast();
  useEffect(() => {
    api.get("/api/dashboard/")
      .then(({data}) => setDonnees(data))
      .catch((error) => { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); });
    // Le graphique est facultatif : une erreur de liste ne masque pas les indicateurs principaux.
    api.get("/api/ventes/", { params: { periode: "semaine" } })
      .then(({data}) => setVentesSemaine(extraireListe(data)))
      .catch((error) => { const texte = messageErreur(error); setErreurGraphique(texte); notifier(texte, "error"); });
  }, [notifier]);

  if (!donnees && !erreur) return <><div className="mb-6"><h1 className="workspace-title">Vue d’ensemble</h1><p className="workspace-subtitle">Un aperçu rapide de votre activité.</p></div><div className="stat-grid">{[1,2,3,4].map((n) => <SkeletonCard key={n}/>)}</div></>;
  const ruptures = donnees?.produits_en_rupture || [];
  return <>
    <div className="page-heading"><div><h1>Vue d’ensemble</h1><p>Voici les chiffres clés de votre commerce.</p></div><Link to="/ventes/nouvelle" className="btn-primary"><Icon name="plus" size={18}/>Enregistrer une vente</Link></div>
    {erreur && <div className="alert-box" role="alert">{erreur}</div>}
    {donnees && <>
      <section className="stat-grid">{statistiques.map((stat) => <Card className="stat-card" key={stat.cle}><div className="stat-top"><span>{stat.titre}</span><span className="stat-icon" style={{backgroundColor:stat.couleur,color:stat.encre}}><Icon name={stat.icon}/></span></div><p className="stat-value">{formaterFCFA(donnees[stat.cle])}</p></Card>)}</section>
      <div className="dashboard-lower">
        <Card><div className="section-card-heading"><div><h2>Activité de la semaine</h2><p>Ventes enregistrées, du lundi au dimanche</p></div><Badge tone="green">Cette semaine</Badge></div>{erreurGraphique?<div className="alert-box">{erreurGraphique}</div>:<GraphiqueVentes ventes={ventesSemaine}/>}</Card>
        <Card><div className="section-card-heading"><div><h2>Stock à surveiller</h2><p>Produits au seuil d’alerte ou en dessous</p></div><Badge tone={ruptures.length ? "amber" : "green"}>{ruptures.length} produit{ruptures.length > 1 ? "s" : ""}</Badge></div>
          {ruptures.length ? <div className="table-list">{ruptures.slice(0,5).map((produit) => <div className="list-row" key={produit.id}><div className="flex min-w-0 items-center gap-3"><span className="empty-icon !h-10 !w-10 !rounded-xl"><Icon name="box" size={18}/></span><div className="min-w-0"><strong className="block truncate text-sm">{produit.nom}</strong><small className="text-ink-muted">Seuil : {produit.seuil_alerte}</small></div></div><Badge tone={produit.quantite_stock === 0 ? "red" : "amber"}>{produit.quantite_stock} restant{produit.quantite_stock > 1 ? "s" : ""}</Badge></div>)}</div> : <div className="empty-state !py-5"><span className="empty-icon"><Icon name="check" size={23}/></span><h3>Stock en ordre</h3><p>Aucun produit sous le seuil d’alerte.</p></div>}
          <Link to="/produits" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand">Voir les produits <Icon name="arrow" size={15}/></Link>
        </Card>
      </div>
      <div className="mt-4 flex justify-end"><Link to="/ventes/historique" className="btn-ghost">Consulter l’historique <Icon name="arrow" size={16}/></Link></div>
    </>}
  </>;
}
