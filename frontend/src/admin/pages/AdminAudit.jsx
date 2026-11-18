import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminPagination, AdminTitre, formatDate } from "../AdminComponents";
import { TexteLocalise, traduire } from "../../contexte/LangueContext";

const actionsAudit = [
  ["creation", "Création"], ["modification", "Modification"], ["suppression", "Suppression"],
  ["changement_stock", "Changement de stock"], ["connexion_reussie", "Connexion réussie"],
  ["connexion_echouee", "Connexion échouée"], ["changement_abonnement", "Abonnement"],
  ["creation_sous_admin", "Création sous-admin"], ["modification_sous_admin", "Modification sous-admin"],
  ["desactivation_sous_admin", "Désactivation sous-admin"], ["suspension_utilisateur", "Suspension commerçant"],
  ["reactivation_utilisateur", "Réactivation commerçant"], ["validation_paiement_admin", "Validation paiement"],
  ["rejet_paiement_admin", "Rejet paiement"],
];

export default function AdminAudit() {
  const [filtres, setFiltres] = useState({ date_debut: "", date_fin: "", action: "", admin: "" });
  const [appliques, setAppliques] = useState(filtres);
  const [page, setPage] = useState(1);
  const [donnees, setDonnees] = useState({ results: [], count: 0 });
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const charger = useCallback(async () => {
    setChargement(true); setErreur("");
    try { const { data } = await adminApi.get("/api/admin/audit/", { params: { ...appliques, admin: appliques.admin || undefined, action: appliques.action || undefined, date_debut: appliques.date_debut || undefined, date_fin: appliques.date_fin || undefined, page } }); setDonnees(data); }
    catch (error) { setErreur(erreurAdmin(error)); }
    finally { setChargement(false); }
  }, [appliques, page]);
  useEffect(() => { charger(); }, [charger]);
  const changer = (key, value) => setFiltres((precedents) => ({ ...precedents, [key]: value }));
  const appliquer = (event) => { event.preventDefault(); setAppliques(filtres); setPage(1); };

  return <><AdminTitre titre="Journal d’audit" description="Historique des actions et décisions enregistrées sur la plateforme."/><AdminErreur>{erreur}</AdminErreur><form className="admin-audit-filters" onSubmit={appliquer}><label className="admin-filter-label">{<TexteLocalise phrase={"Du"} />}<input type="date" value={filtres.date_debut} onChange={(e) => changer("date_debut", e.target.value)}/></label><label className="admin-filter-label">{<TexteLocalise phrase={"Au"} />}<input type="date" value={filtres.date_fin} onChange={(e) => changer("date_fin", e.target.value)}/></label><label className="admin-filter-label">{<TexteLocalise phrase={"Type d’action"} />}<select value={filtres.action} onChange={(e) => changer("action", e.target.value)}><option value="">{<TexteLocalise phrase={"Toutes les actions"} />}</option>{actionsAudit.map(([value, label]) => <option value={value} key={value}>{traduire(label)}</option>)}</select></label><label className="admin-filter-label admin-audit-admin">{<TexteLocalise phrase={"Responsable"} />}<input value={filtres.admin} onChange={(e) => changer("admin", e.target.value)} placeholder={traduire("Email ou identifiant UUID")}/></label><button className="admin-button admin-button-primary">{<TexteLocalise phrase={"Appliquer les filtres"} />}</button></form>
    <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{<TexteLocalise phrase={"Date"} />}</th><th>{<TexteLocalise phrase={"Action"} />}</th><th>{<TexteLocalise phrase={"Responsable"} />}</th><th>{<TexteLocalise phrase={"Commerçant concerné"} />}</th><th>{<TexteLocalise phrase={"Objet"} />}</th><th>{<TexteLocalise phrase={"Détails"} />}</th></tr></thead><tbody>{!chargement && donnees.results.map((log) => <tr key={log.id}><td className="admin-nowrap">{formatDate(log.date, true)}</td><td><AdminBadge tone={log.action.includes("rejet") || log.action.includes("suspension") ? "red" : log.action.includes("validation") || log.action.includes("reactivation") ? "green" : "neutral"}>{actionsAudit.find(([key]) => key === log.action)?.[1] || log.action}</AdminBadge></td><td>{log.admin_responsable || "Système"}</td><td>{log.commercant_email || "—"}</td><td><strong>{log.objet_type}</strong><small>{log.objet_id}</small></td><td><details className="admin-audit-details"><summary>{<TexteLocalise phrase={"Afficher"} />}</summary><pre>{JSON.stringify({ avant: log.anciennes_valeurs, apres: log.nouvelles_valeurs }, null, 2)}</pre></details></td></tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide/>}</div><AdminPagination page={page} setPage={setPage} count={donnees.count}/>
  </>;
}
