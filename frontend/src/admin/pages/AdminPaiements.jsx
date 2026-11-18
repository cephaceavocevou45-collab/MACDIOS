import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminModal, AdminPagination, AdminTitre, formatDate, formatFcfa } from "../AdminComponents";
import { TexteLocalise, traduire } from "../../contexte/LangueContext";

export default function AdminPaiements() {
  const [donnees, setDonnees] = useState({ results: [], count: 0 });
  const [page, setPage] = useState(1);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [selection, setSelection] = useState(null);
  const [motif, setMotif] = useState("");
  const [traitement, setTraitement] = useState(false);
  const [preuve, setPreuve] = useState(null);
  const [preuveUrl, setPreuveUrl] = useState("");

  const charger = useCallback(async () => {
    setChargement(true); setErreur("");
    try { const { data } = await adminApi.get("/api/admin/paiements-en-attente/", { params: { page } }); setDonnees(data); }
    catch (error) { setErreur(erreurAdmin(error)); }
    finally { setChargement(false); }
  }, [page]);
  useEffect(() => { charger(); }, [charger]);
  useEffect(() => () => { if (preuveUrl) URL.revokeObjectURL(preuveUrl); }, [preuveUrl]);

  const afficherPreuve = async (demande) => {
    setErreur("");
    try {
      const { data } = await adminApi.get(`/api/admin/paiements-en-attente/${demande.id}/preuve/`, { responseType: "blob" });
      if (preuveUrl) URL.revokeObjectURL(preuveUrl);
      const url = URL.createObjectURL(data);
      setPreuveUrl(url); setPreuve(demande);
    } catch (error) { setErreur(erreurAdmin(error)); }
  };

  const decider = async () => {
    if (!selection) return;
    setTraitement(true); setErreur("");
    try {
      const valider = selection.action === "valider";
      await adminApi.post(`/api/admin/paiements-en-attente/${selection.demande.id}/${selection.action}/`, valider ? {} : { motif });
      setSelection(null); setMotif(""); await charger();
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setTraitement(false); }
  };

  return <><AdminTitre titre="Paiements en attente" description="Vérifiez les paiements Mobile Money avant de les valider."/><AdminErreur>{erreur}</AdminErreur><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{<TexteLocalise phrase={"Commerçant"} />}</th><th>{<TexteLocalise phrase={"Formule"} />}</th><th>{<TexteLocalise phrase={"Montant"} />}</th><th>{<TexteLocalise phrase={"Référence reçue"} />}</th><th>{<TexteLocalise phrase={"Demande"} />}</th><th>{<TexteLocalise phrase={"Preuve"} />}</th><th>{<TexteLocalise phrase={"Décision"} />}</th></tr></thead><tbody>{!chargement && donnees.results.map((demande) => <tr key={demande.id}><td><strong>{demande.nom_boutique}</strong><small>{demande.commercant_email}</small></td><td>{demande.plan_nom}</td><td className="admin-nowrap">{formatFcfa(demande.montant)}</td><td><code>{demande.reference_transaction}</code></td><td>{formatDate(demande.date_demande, true)}</td><td>{demande.preuve_disponible ? <button className="admin-button admin-button-secondary admin-button-small" onClick={() => afficherPreuve(demande)}>{<TexteLocalise phrase={"Voir la preuve"} />}</button> : <AdminBadge>{<TexteLocalise phrase={"Sans preuve"} />}</AdminBadge>}</td><td><div className="admin-row-actions"><button className="admin-button admin-button-primary admin-button-small" onClick={() => setSelection({ demande, action: "valider" })}>{<TexteLocalise phrase={"Valider"} />}</button><button className="admin-button admin-button-danger admin-button-small" onClick={() => setSelection({ demande, action: "rejeter" })}>{<TexteLocalise phrase={"Rejeter"} />}</button></div></td></tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide>{<TexteLocalise phrase={"Il n’y a aucune demande en attente."} />}</AdminEtatVide>}</div><AdminPagination page={page} setPage={setPage} count={donnees.count}/>
    {selection && <AdminModal titre={selection.action === "valider" ? "Valider ce paiement ?" : "Rejeter ce paiement ?"} onClose={() => { setSelection(null); setMotif(""); }}><div className="admin-payment-summary"><strong>{selection.demande.nom_boutique}</strong><span>{selection.demande.plan_nom} · {formatFcfa(selection.demande.montant)}</span><small>{<TexteLocalise phrase={"Référence :"} />}{' '}{selection.demande.reference_transaction}</small></div>{selection.action === "rejeter" && <label className="admin-field">{<TexteLocalise phrase={"Motif obligatoire"} />}<textarea rows="3" maxLength="250" value={motif} onChange={(e) => setMotif(e.target.value)} placeholder={traduire("Ex. Référence introuvable")}/></label>}<p className="admin-modal-copy">{<TexteLocalise phrase={"Cette décision sera enregistrée dans le journal d’audit."} />}</p><div className="admin-modal-actions"><button className="admin-button admin-button-secondary" onClick={() => setSelection(null)}>{<TexteLocalise phrase={"Annuler"} />}</button><button className={`admin-button ${selection.action === "valider" ? "admin-button-primary" : "admin-button-danger"}`} disabled={traitement || (selection.action === "rejeter" && !motif.trim())} onClick={decider}>{traitement ? "Traitement…" : selection.action === "valider" ? "Confirmer la validation" : "Confirmer le rejet"}</button></div></AdminModal>}
    {preuve && <AdminModal titre={`Preuve · ${preuve.nom_boutique}`} onClose={() => { setPreuve(null); setPreuveUrl(""); }}><img src={preuveUrl} className="admin-proof-image" alt={`Preuve de paiement de ${preuve.nom_boutique}`}/><p className="admin-modal-copy">{<TexteLocalise phrase={"Référence :"} />}{' '}{preuve.reference_transaction} · {formatDate(preuve.date_demande, true)}</p></AdminModal>}
  </>;
}
