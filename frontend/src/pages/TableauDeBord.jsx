import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { formaterFCFA } from "../utils";
import { localePourLangue, TexteLocalise, traduire, useLangue } from "../contexte/LangueContext";

const statistiques = [
  { cle: "ventes_jour", titre: "Chiffre d’affaires aujourd’hui", icon: "cart", couleur: "#eaf5ef", encre: "#006747" },
  { cle: "ventes_semaine", titre: "Chiffre d’affaires cette semaine", icon: "chart", couleur: "#fff2df", encre: "#ac7016" },
  { cle: "ventes_mois", titre: "Chiffre d’affaires ce mois", icon: "wallet", couleur: "#edf0fa", encre: "#5868a7" },
  { cle: "benefice_brut_jour", titre: "Bénéfice brut aujourd’hui", icon: "chart", couleur: "#e8f6f2", encre: "#087d69" },
  { cle: "benefice_brut_semaine", titre: "Bénéfice brut cette semaine", icon: "chart", couleur: "#f1f4e7", encre: "#637b25" },
  { cle: "benefice_brut_mois", titre: "Bénéfice brut ce mois", icon: "wallet", couleur: "#eaf1f8", encre: "#376d9a" },
  { cle: "total_dettes_en_cours", titre: "Dettes en cours", icon: "users", couleur: "#fbeeed", encre: "#a7463d" },
];

const periodeBenefice = {
  benefice_brut_jour: { revenus: "ventes_jour", sansCout: "ventes_sans_cout_jour" },
  benefice_brut_semaine: { revenus: "ventes_semaine", sansCout: "ventes_sans_cout_semaine" },
  benefice_brut_mois: { revenus: "ventes_mois", sansCout: "ventes_sans_cout_mois" },
};

function GraphiqueVentes({ ventes, jours }) {
  const totaux = Array(7).fill(0);
  ventes.forEach((vente) => {
    totaux[vente.jour_semaine] = Number(vente.total || 0);
  });
  const max = Math.max(...totaux, 1);
  const x0 = 30, largeur = 470, haut = 145, baseY = 162;
  const barWidth = 31, espace = largeur / 7;
  return <div className="chart-wrap"><svg viewBox="0 0 530 195" role="img" aria-label={traduire("Montant des ventes par jour cette semaine")}>
    {[25, 70, 115, 160].map((y) => <line key={y} className="chart-grid-line" x1="25" x2="510" y1={y} y2={y}/>)}
    {totaux.map((valeur, index) => {
      const hauteur = Math.max((valeur / max) * haut, valeur ? 9 : 3);
      const x = x0 + index * espace + (espace - barWidth) / 2;
      return <g key={jours[index]}><rect className="chart-bar" x={x} y={baseY - hauteur} width={barWidth} height={hauteur} rx="8" opacity={valeur ? 1 : .18}/><text className="chart-label" x={x + barWidth / 2} y="185" textAnchor="middle">{jours[index]}</text></g>;
    })}
  </svg></div>;
}

export default function TableauDeBord() {
  const { langue } = useLangue();
  const jours = Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(localePourLangue(langue), { weekday: "short" }).format(new Date(2024, 0, index + 1)));
  const [donnees, setDonnees] = useState(null);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();
  useEffect(() => {
    api.get("/api/dashboard/")
      .then(({data}) => setDonnees(data))
      .catch((error) => { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); });
  }, [notifier]);

  if (!donnees && !erreur) return <><div className="mb-6"><h1 className="workspace-title">{<TexteLocalise phrase={"Vue d’ensemble"} />}</h1><p className="workspace-subtitle">{<TexteLocalise phrase={"Un aperçu rapide de votre activité."} />}</p></div><div className="stat-grid">{[1,2,3,4].map((n) => <SkeletonCard key={n}/>)}</div></>;
  const ruptures = donnees?.produits_en_rupture || [];
  return <>
    <div className="page-heading"><div><h1>{<TexteLocalise phrase={"Vue d’ensemble"} />}</h1><p>{<TexteLocalise phrase={"Voici les chiffres clés de votre commerce."} />}</p></div><Link to="/ventes/nouvelle" className="btn-primary"><Icon name="plus" size={18}/>{<TexteLocalise phrase={"Enregistrer une vente"} />}</Link></div>
    {erreur && <div className="alert-box" role="alert">{erreur}</div>}
    {donnees && <>
      <section className="stat-grid">{statistiques.map((stat) => {
        const periode = periodeBenefice[stat.cle];
        const coutsManquants = periode ? Number(donnees[periode.sansCout] || 0) : 0;
        const absenceVente = periode && Number(donnees[periode.revenus] || 0) === 0;
        const valeurManquante = periode
          ? (coutsManquants ? "Coût d’achat incomplet" : "Aucune vente")
          : "À calculer";
        return <Card className="stat-card" key={stat.cle}><div className="stat-top"><span><TexteLocalise phrase={stat.titre}/></span><span className="stat-icon" style={{backgroundColor:stat.couleur,color:stat.encre}}><Icon name={stat.icon}/></span></div><p className="stat-value">{donnees[stat.cle] == null ? <small><TexteLocalise phrase={absenceVente ? "Aucune vente" : valeurManquante}/></small> : formaterFCFA(donnees[stat.cle])}</p></Card>;
      })}</section>
      <div className="mt-5 mb-5 space-y-2 text-sm leading-6 text-ink-muted">
        <p><TexteLocalise phrase="Le bénéfice brut déduit le coût d’achat des produits vendus. Il ne déduit pas les autres charges ou taxes."/></p>
        {(donnees.ventes_sans_cout_jour || donnees.ventes_sans_cout_semaine || donnees.ventes_sans_cout_mois) > 0 && <p role="status"><TexteLocalise phrase="Certaines ventes n’ont pas de coût d’achat enregistré. Le bénéfice reste masqué pour éviter un chiffre incomplet."/> <Link className="font-semibold text-brand underline" to="/produits"><TexteLocalise phrase="Renseigner les coûts des produits"/></Link></p>}
      </div>
      <div className="dashboard-lower">
        <Card><div className="section-card-heading"><div><h2>{<TexteLocalise phrase={"Activité de la semaine"} />}</h2><p>{<TexteLocalise phrase={"Ventes enregistrées, du lundi au dimanche"} />}</p></div><Badge tone="green">{<TexteLocalise phrase={"Cette semaine"} />}</Badge></div><GraphiqueVentes ventes={donnees.ventes_semaine_jour || []} jours={jours}/></Card>
        <Card><div className="section-card-heading"><div><h2>{<TexteLocalise phrase={"Stock à surveiller"} />}</h2><p>{<TexteLocalise phrase={"Produits au seuil d’alerte ou en dessous"} />}</p></div><Badge tone={ruptures.length ? "amber" : "green"}>{ruptures.length}{' '}{<TexteLocalise phrase={"produit"} />}{ruptures.length > 1 ? "s" : ""}</Badge></div>
          {ruptures.length ? <div className="table-list">{ruptures.slice(0,5).map((produit) => <div className="list-row" key={produit.id}><div className="flex min-w-0 items-center gap-3"><span className="empty-icon !h-10 !w-10 !rounded-xl"><Icon name="box" size={18}/></span><div className="min-w-0"><strong className="block truncate text-sm">{produit.nom}</strong><small className="text-ink-muted">{<TexteLocalise phrase={"Seuil :"} />}{' '}{produit.seuil_alerte}</small></div></div><Badge tone={produit.quantite_stock === 0 ? "red" : "amber"}>{produit.quantite_stock}{' '}{<TexteLocalise phrase={"restant"} />}{produit.quantite_stock > 1 ? "s" : ""}</Badge></div>)}</div> : <div className="empty-state !py-5"><span className="empty-icon"><Icon name="check" size={23}/></span><h3>{<TexteLocalise phrase={"Stock en ordre"} />}</h3><p>{<TexteLocalise phrase={"Aucun produit sous le seuil d’alerte."} />}</p></div>}
          <Link to="/produits" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand">{<TexteLocalise phrase={"Voir les produits"} />}{' '}<Icon name="arrow" size={15}/></Link>
        </Card>
      </div>
      <div className="mt-4 flex justify-end"><Link to="/ventes/historique" className="btn-ghost">{<TexteLocalise phrase={"Consulter l’historique"} />}{' '}<Icon name="arrow" size={16}/></Link></div>
    </>}
  </>;
}
