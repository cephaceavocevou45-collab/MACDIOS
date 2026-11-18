import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminPagination, AdminTitre, formatDate, AdminModal } from "../AdminComponents";
import { useAdminAuth, aPermission } from "../AdminAuthContext";
import { TexteLocalise, traduire } from "../../contexte/LangueContext";

const statutLibelle = { actif: "Actif", essai: "Essai", expire: "Expiré" };

export default function AdminUtilisateurs() {
  const { administrateur } = useAdminAuth();
  const peutSuspendre = aPermission(administrateur, "suspendre_utilisateur");
  const [recherche, setRecherche] = useState("");
  const [statut, setStatut] = useState("");
  const [page, setPage] = useState(1);
  const [donnees, setDonnees] = useState({ results: [], count: 0 });
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [selection, setSelection] = useState(null);
  const [motif, setMotif] = useState("");
  const [traitement, setTraitement] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true); setErreur("");
    try { const { data } = await adminApi.get("/api/admin/utilisateurs/", { params: { recherche: recherche || undefined, statut_abonnement: statut || undefined, page } }); setDonnees(data); }
    catch (error) { setErreur(erreurAdmin(error)); }
    finally { setChargement(false); }
  }, [recherche, statut, page]);

  useEffect(() => { const timer = window.setTimeout(charger, 250); return () => window.clearTimeout(timer); }, [charger]);

  const confirmer = async () => {
    if (!selection) return;
    setTraitement(true); setErreur("");
    try {
      const suspendre = selection.action === "suspendre";
      await adminApi.post(`/api/admin/utilisateurs/${selection.user.id}/${suspendre ? "suspendre" : "reactiver"}/`, suspendre ? { motif } : {});
      setSelection(null); setMotif(""); await charger();
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setTraitement(false); }
  };

  return <><AdminTitre titre="Commerçants" description="Consultez les comptes et gérez leur accès à la plateforme."/><AdminErreur>{erreur}</AdminErreur><div className="admin-toolbar"><label className="admin-search">⌕<input value={recherche} onChange={(e) => { setRecherche(e.target.value); setPage(1); }} placeholder={traduire("Rechercher par nom ou email")}/></label><label className="admin-filter-label">{<TexteLocalise phrase={"Abonnement"} />}<select value={statut} onChange={(e) => { setStatut(e.target.value); setPage(1); }}><option value="">{<TexteLocalise phrase={"Tous les statuts"} />}</option><option value="actif">{<TexteLocalise phrase={"Actif"} />}</option><option value="essai">{<TexteLocalise phrase={"Essai"} />}</option><option value="expire">{<TexteLocalise phrase={"Expiré"} />}</option></select></label></div>
    <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{<TexteLocalise phrase={"Boutique / commerçant"} />}</th><th>{<TexteLocalise phrase={"Abonnement"} />}</th><th>{<TexteLocalise phrase={"Fin d’accès"} />}</th><th>{<TexteLocalise phrase={"État du compte"} />}</th><th>{<TexteLocalise phrase={"Inscrit le"} />}</th>{peutSuspendre && <th>{<TexteLocalise phrase={"Action"} />}</th>}</tr></thead><tbody>{!chargement && donnees.results.map((user) => <tr key={user.id}><td><strong>{user.nom_boutique || "Boutique"}</strong><small>{user.email}</small></td><td><AdminBadge tone={user.statut_abonnement === "expire" ? "red" : user.statut_abonnement === "essai" ? "amber" : "green"}>{statutLibelle[user.statut_abonnement] || "Sans abonnement"}</AdminBadge></td><td>{formatDate(user.date_fin_abonnement)}</td><td><AdminBadge tone={user.is_active ? "green" : "red"}>{user.is_active ? "Actif" : "Suspendu"}</AdminBadge>{user.motif_suspension && <small className="admin-subtext">{user.motif_suspension}</small>}</td><td>{formatDate(user.date_joined)}</td>{peutSuspendre && <td>{user.is_active ? <button className="admin-button admin-button-danger admin-button-small" onClick={() => setSelection({ user, action: "suspendre" })}>{<TexteLocalise phrase={"Suspendre"} />}</button> : <button className="admin-button admin-button-secondary admin-button-small" onClick={() => setSelection({ user, action: "reactiver" })}>{<TexteLocalise phrase={"Réactiver"} />}</button>}</td>}</tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide/>}</div><AdminPagination page={page} setPage={setPage} count={donnees.count}/>
    {selection && <AdminModal titre={selection.action === "suspendre" ? "Suspendre ce compte ?" : "Réactiver ce compte ?"} onClose={() => { setSelection(null); setMotif(""); }}><p className="admin-modal-copy"><strong>{selection.user.nom_boutique}</strong><br/>{selection.user.email}</p>{selection.action === "suspendre" && <label className="admin-field">{<TexteLocalise phrase={"Motif obligatoire"} />}<textarea rows="3" maxLength="250" value={motif} onChange={(e) => setMotif(e.target.value)} placeholder={traduire("Indiquez la raison de la suspension")}/></label>}<div className="admin-modal-actions"><button className="admin-button admin-button-secondary" onClick={() => setSelection(null)}>{<TexteLocalise phrase={"Annuler"} />}</button><button className={`admin-button ${selection.action === "suspendre" ? "admin-button-danger" : "admin-button-primary"}`} disabled={traitement || (selection.action === "suspendre" && !motif.trim())} onClick={confirmer}>{traitement ? "Traitement…" : selection.action === "suspendre" ? "Confirmer la suspension" : "Réactiver le compte"}</button></div></AdminModal>}
  </>;
}
