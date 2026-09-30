import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminPagination, AdminTitre, formatDate, AdminModal } from "../AdminComponents";
import { useAdminAuth, aPermission } from "../AdminAuthContext";

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

  return <><AdminTitre titre="Commerçants" description="Consultez les comptes et gérez leur accès à la plateforme."/><AdminErreur>{erreur}</AdminErreur><div className="admin-toolbar"><label className="admin-search">⌕<input value={recherche} onChange={(e) => { setRecherche(e.target.value); setPage(1); }} placeholder="Rechercher par nom ou email"/></label><label className="admin-filter-label">Abonnement<select value={statut} onChange={(e) => { setStatut(e.target.value); setPage(1); }}><option value="">Tous les statuts</option><option value="actif">Actif</option><option value="essai">Essai</option><option value="expire">Expiré</option></select></label></div>
    <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Boutique / commerçant</th><th>Abonnement</th><th>Fin d’accès</th><th>État du compte</th><th>Inscrit le</th>{peutSuspendre && <th>Action</th>}</tr></thead><tbody>{!chargement && donnees.results.map((user) => <tr key={user.id}><td><strong>{user.nom_boutique || "Boutique"}</strong><small>{user.email}</small></td><td><AdminBadge tone={user.statut_abonnement === "expire" ? "red" : user.statut_abonnement === "essai" ? "amber" : "green"}>{statutLibelle[user.statut_abonnement] || "Sans abonnement"}</AdminBadge></td><td>{formatDate(user.date_fin_abonnement)}</td><td><AdminBadge tone={user.is_active ? "green" : "red"}>{user.is_active ? "Actif" : "Suspendu"}</AdminBadge>{user.motif_suspension && <small className="admin-subtext">{user.motif_suspension}</small>}</td><td>{formatDate(user.date_joined)}</td>{peutSuspendre && <td>{user.is_active ? <button className="admin-button admin-button-danger admin-button-small" onClick={() => setSelection({ user, action: "suspendre" })}>Suspendre</button> : <button className="admin-button admin-button-secondary admin-button-small" onClick={() => setSelection({ user, action: "reactiver" })}>Réactiver</button>}</td>}</tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide/>}</div><AdminPagination page={page} setPage={setPage} count={donnees.count}/>
    {selection && <AdminModal titre={selection.action === "suspendre" ? "Suspendre ce compte ?" : "Réactiver ce compte ?"} onClose={() => { setSelection(null); setMotif(""); }}><p className="admin-modal-copy"><strong>{selection.user.nom_boutique}</strong><br/>{selection.user.email}</p>{selection.action === "suspendre" && <label className="admin-field">Motif obligatoire<textarea rows="3" maxLength="250" value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Indiquez la raison de la suspension"/></label>}<div className="admin-modal-actions"><button className="admin-button admin-button-secondary" onClick={() => setSelection(null)}>Annuler</button><button className={`admin-button ${selection.action === "suspendre" ? "admin-button-danger" : "admin-button-primary"}`} disabled={traitement || (selection.action === "suspendre" && !motif.trim())} onClick={confirmer}>{traitement ? "Traitement…" : selection.action === "suspendre" ? "Confirmer la suspension" : "Réactiver le compte"}</button></div></AdminModal>}
  </>;
}
