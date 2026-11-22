import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminModal, AdminPagination, AdminTitre, formatDate, formatFcfa } from "../AdminComponents";
import { TexteLocalise, traduire } from "../../contexte/LangueContext";

const ONGLETS = [
  ["en_attente", "En cours"], ["a_valider", "À valider"], ["reussi", "Validés"],
  ["echecs", "Échoués / annulés"], ["reclamations", "Signalements"], ["manuel", "Demandes manuelles"],
];

export default function AdminPaiements() {
  const [onglet, setOnglet] = useState("en_attente");
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
    try {
      let url = "/api/admin/paiements-fedapay/";
      const params = { page };
      if (onglet === "reclamations") url = "/api/admin/reclamations-paiement/";
      else if (onglet === "manuel") url = "/api/admin/paiements-en-attente/";
      else params.statut = onglet;
      const { data } = await adminApi.get(url, { params });
      setDonnees(data);
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setChargement(false); }
  }, [onglet, page]);
  useEffect(() => { charger(); }, [charger]);
  useEffect(() => {
    const timer = window.setInterval(charger, 30000);
    return () => window.clearInterval(timer);
  }, [charger]);
  useEffect(() => () => { if (preuveUrl) URL.revokeObjectURL(preuveUrl); }, [preuveUrl]);

  function changerOnglet(id) { setOnglet(id); setPage(1); setSelection(null); }

  const afficherPreuve = async (demande) => {
    setErreur("");
    try {
      const { data } = await adminApi.get(`/api/admin/paiements-en-attente/${demande.id}/preuve/`, { responseType: "blob" });
      if (preuveUrl) URL.revokeObjectURL(preuveUrl);
      const url = URL.createObjectURL(data);
      setPreuveUrl(url); setPreuve(demande);
    } catch (error) { setErreur(erreurAdmin(error)); }
  };

  const deciderManuel = async () => {
    if (!selection) return;
    setTraitement(true); setErreur("");
    try {
      const valider = selection.action === "valider";
      await adminApi.post(`/api/admin/paiements-en-attente/${selection.item.id}/${selection.action}/`, valider ? {} : { motif });
      setSelection(null); setMotif(""); await charger();
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setTraitement(false); }
  };

  const validerFedaPay = async () => {
    if (!selection) return;
    setTraitement(true); setErreur("");
    try {
      await adminApi.post(`/api/admin/paiements-fedapay/${selection.item.reference}/valider/`, {});
      setSelection(null); await charger();
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setTraitement(false); }
  };

  const titre = onglet === "manuel" ? "Demandes manuelles en attente" : "Suivi des paiements";
  return <>
    <AdminTitre titre={titre} description="Paiements FedaPay, validations d’équipe, échecs et signalements des commerçants."/>
    <AdminErreur>{erreur}</AdminErreur>
    <div className="admin-payment-tabs" role="tablist" aria-label="Catégories de paiements">
      {ONGLETS.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={onglet === id} className={`admin-button admin-button-small ${onglet === id ? "admin-button-primary" : "admin-button-secondary"}`} onClick={() => changerOnglet(id)}>{traduire(label)}</button>)}
    </div>

    {onglet === "manuel" ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{<TexteLocalise phrase={"Commerçant"}/>}</th><th>{<TexteLocalise phrase={"Formule"}/>}</th><th>{<TexteLocalise phrase={"Montant"}/>}</th><th>{<TexteLocalise phrase={"Référence reçue"}/>}</th><th>{<TexteLocalise phrase={"Demande"}/>}</th><th>{<TexteLocalise phrase={"Preuve"}/>}</th><th>{<TexteLocalise phrase={"Décision"}/>}</th></tr></thead><tbody>{!chargement && donnees.results.map((item) => <tr key={item.id}><td><strong>{item.nom_boutique}</strong><small>{item.commercant_email || item.operateur_nom}</small></td><td>{item.plan_nom}</td><td className="admin-nowrap">{formatFcfa(item.montant)}</td><td><code>{item.reference_transaction}</code></td><td>{formatDate(item.date_demande, true)}</td><td>{item.preuve_disponible ? <button className="admin-button admin-button-secondary admin-button-small" onClick={() => afficherPreuve(item)}>{<TexteLocalise phrase={"Voir la preuve"}/>}</button> : <AdminBadge>{<TexteLocalise phrase={"Sans preuve"}/>}</AdminBadge>}</td><td><div className="admin-row-actions"><button className="admin-button admin-button-primary admin-button-small" onClick={() => setSelection({ item, action: "valider" })}>{<TexteLocalise phrase={"Valider"}/>}</button><button className="admin-button admin-button-danger admin-button-small" onClick={() => setSelection({ item, action: "rejeter" })}>{<TexteLocalise phrase={"Rejeter"}/>}</button></div></td></tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide>Il n’y a aucune demande manuelle en attente.</AdminEtatVide>}</div>
      : onglet === "reclamations" ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Commerçant</th><th>Formule / montant</th><th>Référence</th><th>Signalement</th><th>Reçu le</th></tr></thead><tbody>{!chargement && donnees.results.map((item) => <tr key={item.id}><td><strong>{item.nom_boutique}</strong><small>{item.telephone}</small></td><td>{item.plan_nom}<small>{formatFcfa(item.montant)}</small></td><td><code>{item.reference}</code></td><td className="admin-payment-complaint">{item.description}</td><td>{formatDate(item.date_creation, true)}</td></tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide>Aucun signalement de paiement reçu.</AdminEtatVide>}</div>
        : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Commerçant</th><th>Formule / montant</th><th>Référence FedaPay</th><th>État</th><th>Dernière étape</th>{onglet === "a_valider" && <th>Décision</th>}</tr></thead><tbody>{!chargement && donnees.results.map((item) => <tr key={item.reference}><td><strong>{item.nom_boutique}</strong><small>{item.commercant_telephone}{item.commercant_email ? ` · ${item.commercant_email}` : ""}</small></td><td>{item.plan_nom}<small>{formatFcfa(item.montant)}</small></td><td><code>{item.fedapay_transaction_id || item.reference}</code></td><td><AdminBadge tone={item.statut === "reussi" ? "green" : item.statut === "a_valider" ? "amber" : ["echoue", "annule"].includes(item.statut) ? "red" : "neutral"}>{({ en_attente: "En attente FedaPay", a_valider: "À valider par l’équipe", reussi: "Validé", echoue: "Échoué", annule: "Annulé" })[item.statut] || item.statut}</AdminBadge></td><td>{formatDate(item.date_validation || item.date_confirmation_fedapay || item.date_creation, true)}{item.valide_par_nom && <small>Validé par {item.valide_par_nom}</small>}</td>{onglet === "a_valider" && <td><button className="admin-button admin-button-primary admin-button-small" onClick={() => setSelection({ item, action: "valider-fedapay" })}>Valider l’abonnement</button></td>}</tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide>{({ en_attente: "Aucun paiement FedaPay en attente.", a_valider: "Aucun paiement confirmé à valider.", reussi: "Aucun paiement validé.", echecs: "Aucun paiement échoué ou annulé." })[onglet] || "Aucun résultat."}</AdminEtatVide>}</div>}
    <AdminPagination page={page} setPage={setPage} count={donnees.count}/>
    {selection && selection.action === "valider-fedapay" && <AdminModal titre="Valider ce paiement confirmé ?" onClose={() => setSelection(null)}><div className="admin-payment-summary"><strong>{selection.item.nom_boutique}</strong><span>{selection.item.plan_nom} · {formatFcfa(selection.item.montant)}</span><small>La transaction sera revérifiée auprès de FedaPay et l’abonnement activé après confirmation.</small></div><div className="admin-modal-actions"><button className="admin-button admin-button-secondary" onClick={() => setSelection(null)}>Annuler</button><button className="admin-button admin-button-primary" disabled={traitement} onClick={validerFedaPay}>{traitement ? "Vérification…" : "Confirmer la validation"}</button></div></AdminModal>}
    {selection && ["valider", "rejeter"].includes(selection.action) && <AdminModal titre={selection.action === "valider" ? "Valider ce paiement ?" : "Rejeter ce paiement ?"} onClose={() => { setSelection(null); setMotif(""); }}><div className="admin-payment-summary"><strong>{selection.item.nom_boutique}</strong><span>{selection.item.plan_nom} · {formatFcfa(selection.item.montant)}</span><small>Référence : {selection.item.reference_transaction}</small></div>{selection.action === "rejeter" && <label className="admin-field">Motif obligatoire<textarea rows="3" maxLength="250" value={motif} onChange={(e) => setMotif(e.target.value)} placeholder={traduire("Ex. Référence introuvable")}/></label>}<p className="admin-modal-copy">Cette décision sera enregistrée dans le journal d’audit.</p><div className="admin-modal-actions"><button className="admin-button admin-button-secondary" onClick={() => setSelection(null)}>Annuler</button><button className={`admin-button ${selection.action === "valider" ? "admin-button-primary" : "admin-button-danger"}`} disabled={traitement || (selection.action === "rejeter" && !motif.trim())} onClick={deciderManuel}>{traitement ? "Traitement…" : "Confirmer"}</button></div></AdminModal>}
    {preuve && <AdminModal titre={`Preuve · ${preuve.nom_boutique}`} onClose={() => { setPreuve(null); setPreuveUrl(""); }}><img src={preuveUrl} className="admin-proof-image" alt={`Preuve de paiement de ${preuve.nom_boutique}`}/><p className="admin-modal-copy">Référence : {preuve.reference_transaction} · {formatDate(preuve.date_demande, true)}</p></AdminModal>}
  </>;
}
