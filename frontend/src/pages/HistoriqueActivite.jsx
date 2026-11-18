import { useCallback, useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { Erreur } from "../composants/Commun";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { TexteLocalise } from "../contexte/LangueContext";
import { afficherDate } from "../utils";

const nomsAction = {
  creation: "Création", modification: "Modification", suppression: "Suppression",
  changement_stock: "Changement de stock", connexion_reussie: "Connexion réussie",
  connexion_echouee: "Connexion échouée", changement_abonnement: "Abonnement",
};

function valeursLisibles(valeurs) {
  if (!valeurs || Object.keys(valeurs).length === 0) return "Aucun détail";
  return Object.entries(valeurs).map(([cle, valeur]) => `${cle.replaceAll("_", " ")} : ${String(valeur ?? "—")}`).join(" · ");
}

export default function HistoriqueActivite() {
  const [evenements, setEvenements] = useState([]);
  const [action, setAction] = useState("");
  const [dateDebut, setDateDebut] = useState("");
  const [dateFin, setDateFin] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur("");
    try {
      const { data } = await api.get("/api/audit/", { params: {
        page, ...(action && { action }), ...(dateDebut && { date_debut: dateDebut }),
        ...(dateFin && { date_fin: dateFin }),
      } });
      setEvenements(data.results || []);
      setPages(data.count ? Math.ceil(data.count / 20) : 1);
    } catch (error) {
      const texte = messageErreur(error);
      setErreur(texte);
      notifier(texte, "error");
    } finally {
      setChargement(false);
    }
  }, [action, dateDebut, dateFin, page, notifier]);

  useEffect(() => { charger(); }, [charger]);

  function filtrer(event) {
    event.preventDefault();
    setPage(1);
  }

  return <div className="page-stack">
    <div className="page-heading"><div><span className="form-eyebrow">{<TexteLocalise phrase={"Sécurité et suivi"} />}</span><h1>{<TexteLocalise phrase={"Historique d'activité"} />}</h1><p>{<TexteLocalise phrase={"Consultez les actions enregistrées dans votre boutique."} />}</p></div><Badge tone="neutral">{evenements.length}{' '}{<TexteLocalise phrase={"sur cette page"} />}</Badge></div>
    <Erreur texte={erreur}/>
    <Card><form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" onSubmit={filtrer}>
      <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Type d'action"} />}</span><select className="field-control" value={action} onChange={(event) => { setAction(event.target.value); setPage(1); }}><option value="">{<TexteLocalise phrase={"Toutes les actions"} />}</option>{Object.entries(nomsAction).map(([cle, nom]) => <option key={cle} value={cle}>{nom}</option>)}</select></label>
      <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"À partir du"} />}</span><input className="field-control" type="date" value={dateDebut} onChange={(event) => setDateDebut(event.target.value)}/></label>
      <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Jusqu'au"} />}</span><input className="field-control" type="date" value={dateFin} onChange={(event) => setDateFin(event.target.value)}/></label>
      <div className="flex items-end"><Button type="submit" className="w-full"><Icon name="check"/>{<TexteLocalise phrase={"Appliquer les dates"} />}</Button></div>
    </form></Card>
    {chargement ? <div className="grid gap-3">{[1, 2, 3].map((n) => <SkeletonCard key={n}/>)}</div> : evenements.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="chart" size={25}/></span><h2>{<TexteLocalise phrase={"Aucune activité à afficher"} />}</h2><p>{<TexteLocalise phrase={"Les prochaines actions enregistrées apparaîtront ici."} />}</p></Card> : <div className="grid gap-3">{evenements.map((item) => <Card key={item.id}>
      <div className="flex flex-wrap items-start justify-between gap-3"><div><Badge tone={item.action === "connexion_echouee" ? "red" : item.action === "suppression" ? "amber" : "green"}>{nomsAction[item.action] || item.action}</Badge><h2 className="mb-1 mt-3 text-lg font-bold">{item.objet_type}{item.objet_id ? ` · ${item.objet_id}` : ""}</h2><p className="m-0 text-sm text-ink-muted">{afficherDate(item.date)}</p></div></div>
      {(Object.keys(item.anciennes_valeurs || {}).length > 0 || Object.keys(item.nouvelles_valeurs || {}).length > 0) && <details className="mt-4 text-sm"><summary className="cursor-pointer font-semibold text-brand">{<TexteLocalise phrase={"Voir les détails enregistrés"} />}</summary><div className="mt-3 grid gap-2 text-ink-muted"><p className="m-0"><strong>{<TexteLocalise phrase={"Avant :"} />}{' '}</strong>{valeursLisibles(item.anciennes_valeurs)}</p><p className="m-0"><strong>{<TexteLocalise phrase={"Après :"} />}{' '}</strong>{valeursLisibles(item.nouvelles_valeurs)}</p></div></details>}
    </Card>)}</div>}
    <div className="flex items-center justify-between gap-3"><Button variant="secondary" disabled={chargement || page <= 1} onClick={() => setPage((p) => p - 1)}>{<TexteLocalise phrase={"Précédent"} />}</Button><span className="text-sm text-ink-muted">{<TexteLocalise phrase={"Page"} />}{' '}{page}{' '}{<TexteLocalise phrase={"sur"} />}{' '}{pages}</span><Button variant="secondary" disabled={chargement || page >= pages} onClick={() => setPage((p) => p + 1)}>{<TexteLocalise phrase={"Suivant"} />}</Button></div>
  </div>;
}
