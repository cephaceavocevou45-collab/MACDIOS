import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import { TexteLocalise } from "../contexte/LangueContext";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import Pagination from "../composants/Pagination";
import { SkeletonCard } from "../composants/Skeleton";
import { extraireListe } from "../utils";

const types = [
  ["", "Tous les mouvements"], ["initial", "Stock initial"], ["achat", "Réception d’achat"],
  ["vente", "Vente"], ["ajustement", "Ajustement manuel"],
];

/** Journal en lecture seule pour expliquer les variations de chaque stock. */
export default function MouvementsStock() {
  const [mouvements, setMouvements] = useState([]);
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setChargement(true);
    try {
      const { data } = await api.get("/api/mouvements-stock/", { params: { page, type: type || undefined } });
      setMouvements(extraireListe(data)); setTotal(data.count ?? extraireListe(data).length); setErreur("");
    } catch (error) { setErreur(messageErreur(error)); }
    finally { setChargement(false); }
  }, [page, type]);
  useEffect(() => { charger(); }, [charger]);

  return <>
    <div className="page-heading"><div><span className="form-eyebrow"><TexteLocalise phrase="Achats et stock"/></span><h1><TexteLocalise phrase="Mouvements de stock"/></h1><p><TexteLocalise phrase="Retrouvez chaque entrée et sortie de stock, sa date et la quantité avant/après."/></p></div><Link className="btn-secondary" to="/approvisionnements"><Icon name="plus" size={17}/><TexteLocalise phrase="Nouvelle réception"/></Link></div>
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <div className="filter-row"><p className="text-sm text-ink-muted">{total} <TexteLocalise phrase="mouvement(s) dans l’historique"/></p><label className="field-wrap max-w-xs"><span className="field-label"><TexteLocalise phrase="Type de mouvement"/></span><select className="field-control" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}>{types.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
    {chargement ? <div className="product-card-grid">{[1, 2, 3].map((n) => <SkeletonCard key={n}/>)}</div> : mouvements.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="clock" size={24}/></span><h2><TexteLocalise phrase="Aucun mouvement à afficher"/></h2><p><TexteLocalise phrase="Les créations, ventes, réceptions et corrections de stock seront conservées ici."/></p></Card> : <Card className="overflow-hidden p-0"><div className="divide-y divide-line">{mouvements.map((m) => <article key={m.id} className="flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5"><div className="flex min-w-0 items-start gap-3"><span className={`product-icon ${m.variation < 0 ? "text-red-700" : "text-emerald-800"}`}><Icon name={m.variation < 0 ? "cart" : "box"} size={19}/></span><div className="min-w-0"><h3 className="truncate font-semibold">{m.produit_nom}</h3><p className="text-sm text-ink-muted">{m.type_libelle} · {new Date(m.date).toLocaleString()}</p>{m.note && <p className="mt-1 text-sm">{m.note}</p>}</div></div><div className="text-right"><strong className={m.variation < 0 ? "text-red-700" : "text-emerald-800"}>{m.variation > 0 ? "+" : ""}{m.variation}</strong><p className="text-xs text-ink-muted"><TexteLocalise phrase="Stock"/> : {m.quantite_avant} → {m.quantite_apres}</p></div></article>)}</div></Card>}
    <Pagination page={page} count={total} onChange={setPage}/>
    <div className="mt-5"><Link to="/produits" className="btn-ghost"><TexteLocalise phrase="Retour aux produits"/></Link></div>
  </>;
}
