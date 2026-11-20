import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import DicteeVocale from "../composants/DicteeVocale";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Modal from "../composants/Modal";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import Pagination from "../composants/Pagination";
import { afficherDate, formaterFCFA } from "../utils";
import { extraireChampsDictee } from "../utils/dicteeVocale";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

export default function DetailClient() {
  const { id } = useParams();
  const [client, setClient] = useState(null);
  const [dettes, setDettes] = useState([]);
  const [action, setAction] = useState("");
  const [detteChoisie, setDetteChoisie] = useState(null);
  const [montant, setMontant] = useState("");
  const [note, setNote] = useState("");
  const [raison, setRaison] = useState("");
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(false);
  const [pdfEnCours, setPdfEnCours] = useState(null);
  const [erreur, setErreur] = useState("");
  const [pageDettes, setPageDettes] = useState(1);
  const [nombreDettes, setNombreDettes] = useState(0);
  const notifier = useToast();

  const charger = useCallback(async () => {
    try {
      const [reponseClient, reponseDettes] = await Promise.all([
        api.get(`/api/clients/${id}/`),
        api.get("/api/dettes/", { params: { client: id, page: pageDettes } }),
      ]);
      setClient(reponseClient.data);
      setDettes(Array.isArray(reponseDettes.data) ? reponseDettes.data : reponseDettes.data.results || []);
      setNombreDettes(reponseDettes.data.count ?? reponseDettes.data.length ?? 0);
      setErreur("");
    } catch (error) {
      const texte = messageErreur(error); setErreur(texte); notifier(texte, "error");
    } finally { setChargement(false); }
  }, [id, pageDettes, notifier]);

  useEffect(() => { charger(); }, [charger]);

  function fermer() {
    setAction(""); setDetteChoisie(null); setMontant(""); setNote(""); setRaison(""); setErreur("");
  }

  function dicterOperation(phrase) {
    const champs = extraireChampsDictee(phrase, {
      montant: { aliases: ["nouveau montant", "montant", "somme", "amount"], type: "number" },
      note: { aliases: ["note", "motif", "description"] },
      raison: { aliases: ["raison", "explication", "reason"] },
    }, null);
    if (champs.montant) setMontant(champs.montant);
    if (champs.note) setNote(champs.note);
    if (champs.raison) setRaison(champs.raison);
  }

  async function envoyer(event) {
    event.preventDefault(); setErreur(""); setEnvoi(true);
    try {
      if (action === "dette") {
        await api.post("/api/dettes/", { client: Number(id), montant: Number(montant), note: note.trim() });
        notifier("Dette ajoutée. Vous pouvez télécharger son reçu PDF.");
      } else if (action === "paiement") {
        await api.post("/api/paiements/", { client: Number(id), montant: Number(montant) });
        notifier("Paiement enregistré.");
      } else {
        await api.post(`/api/dettes/${detteChoisie.id}/correction/`, {
          nouveau_montant: Number(montant), raison: raison.trim(),
        });
        notifier("Correction enregistrée et ajoutée à l’historique de la dette.");
      }
      fermer(); await charger();
    } catch (error) { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); }
    finally { setEnvoi(false); }
  }

  async function telechargerRecu(dette) {
    setPdfEnCours(dette.id);
    try {
      const { data } = await api.get(`/api/dettes/${dette.id}/recu/`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const lien = document.createElement("a");
      lien.href = url; lien.download = `recu-dette-${dette.id}.pdf`;
      document.body.appendChild(lien); lien.click(); lien.remove(); URL.revokeObjectURL(url);
    } catch (error) { notifier(messageErreur(error), "error"); }
    finally { setPdfEnCours(null); }
  }

  if (chargement) return <><div className="page-heading"><div><h1>{<TexteLocalise phrase={"Fiche client"} />}</h1></div></div><SkeletonCard/></>;
  if (!client) return <><Link to="/clients" className="btn-ghost mb-4">{<TexteLocalise phrase={"← Retour aux clients"} />}</Link><div className="alert-box">{erreur || "Client introuvable."}</div></>;
  const solde = Number(client.solde || 0);

  return <>
    <div className="page-heading"><div><Link to="/clients" className="back-link">{<TexteLocalise phrase={"← Tous les clients"} />}</Link><div className="client-detail-title"><span className="client-avatar client-avatar-large">{client.nom?.trim()?.charAt(0)?.toUpperCase() || "C"}</span><div><h1>{client.nom}</h1><p>{client.telephone || "Aucun téléphone renseigné"}</p></div></div></div><div className="flex flex-wrap gap-2"><Badge tone={solde > 0 ? "amber" : "green"}>{solde > 0 ? "Solde à régler" : "Compte à jour"}</Badge>{!client.actif && <Badge tone="neutral">{<TexteLocalise phrase={"Client archivé"} />}</Badge>}</div></div>
    {!client.actif && <div className="alert-box mb-4" role="status">{<TexteLocalise phrase={"Ce client est archivé. Son historique reste consultable, mais aucune nouvelle opération ne peut être enregistrée."} />}</div>}
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <div className="client-detail-grid"><Card className="balance-card"><span className="balance-icon"><Icon name="wallet" size={22}/></span><p>{<TexteLocalise phrase={"Solde en cours"} />}</p><strong>{formaterFCFA(client.solde)}</strong><small>{<TexteLocalise phrase={"Dettes enregistrées moins les paiements reçus"} />}</small></Card><Card className="balance-explainer"><span className="feature-icon"><Icon name="info" size={21}/></span><h2>{<TexteLocalise phrase={"Un suivi clair, au même endroit"} />}</h2><p>{<TexteLocalise phrase={"Ajoutez une dette lorsque votre client achète à crédit. Enregistrez ensuite ses paiements pour actualiser son solde."} />}</p></Card></div>
    {client.actif && <div className="client-actions"><Button onClick={() => setAction("dette")}><Icon name="plus" size={17}/>{<TexteLocalise phrase={"Ajouter une dette"} />}</Button><Button variant="secondary" onClick={() => setAction("paiement")} disabled={solde <= 0}><Icon name="wallet" size={17}/>{<TexteLocalise phrase={"Enregistrer un paiement"} />}</Button></div>}

    <section className="debt-list-section"><div className="section-card-heading"><div><h2>{<TexteLocalise phrase={"Dettes enregistrées"} />}</h2><p>{<TexteLocalise phrase={"Chaque reçu PDF reprend le solde global restant du client."} />}</p></div></div>
      {dettes.length === 0 ? <Card><p className="empty-state">{<TexteLocalise phrase={"Aucune dette enregistrée pour ce client."} />}</p></Card> : <div className="debt-list">{dettes.map((dette) => <Card className="debt-item" key={dette.id}>
        <div className="debt-item-heading"><div><span className="field-hint">{<TexteLocalise phrase={"Dette du"} />}{' '}{afficherDate(dette.date)}</span><strong>{formaterFCFA(dette.montant)}</strong>{dette.note && <p>{dette.note}</p>}</div><Badge tone="amber">{<TexteLocalise phrase={"Dette"} />}</Badge></div>
        {dette.corrections?.length > 0 && <div className="debt-corrections"><strong>{<TexteLocalise phrase={"Historique des corrections"} />}</strong>{dette.corrections.map((correction) => <p key={correction.id}>{afficherDate(correction.date)} : {formaterFCFA(correction.montant_precedent)} → {formaterFCFA(correction.nouveau_montant)} — {correction.raison}</p>)}</div>}
        <div className="debt-item-actions"><Button variant="secondary" onClick={() => telechargerRecu(dette)} disabled={pdfEnCours === dette.id}>{pdfEnCours === dette.id ? "Préparation…" : "Télécharger le reçu (PDF)"}</Button>{client.actif && <Button variant="ghost" onClick={() => { setDetteChoisie(dette); setMontant(dette.montant); setAction("correction"); }}>{<TexteLocalise phrase={"Corriger le montant"} />}</Button>}</div>
      </Card>)}</div>}
      <Pagination page={pageDettes} count={nombreDettes} onChange={setPageDettes}/>
    </section>

    <Modal open={Boolean(action)} title={action === "dette" ? "Ajouter une dette" : action === "paiement" ? "Enregistrer un paiement" : "Corriger le montant"} onClose={fermer}>
      <form onSubmit={envoyer} className="grid gap-4"><p className="m-0 text-sm text-ink-muted">{<TexteLocalise phrase={"Client :"} />}{' '}<strong className="text-ink">{client.nom}</strong></p>
        <DicteeVocale onTranscription={dicterOperation} aide={action === "paiement" ? "Dictez le montant à enregistrer. Exemple : montant 5 000." : action === "correction" ? "Dictez le nouveau montant et la raison. Exemple : nouveau montant 4 000, raison erreur de saisie." : "Dictez le montant de la dette et, si besoin, une note. Exemple : montant 5 000, note achat de marchandises."}/>
        {action === "correction" && <p className="m-0 text-sm text-ink-muted">{<TexteLocalise phrase={"Montant actuel :"} />}{' '}<strong className="text-ink">{formaterFCFA(detteChoisie?.montant)}</strong>{<TexteLocalise phrase={". L’ancien montant et la raison resteront dans l’historique."} />}</p>}
        <Input label={action === "correction" ? "Nouveau montant (FCFA)" : "Montant (FCFA)"} type="number" min="1" step="1" required value={montant} onChange={(event) => setMontant(event.target.value)} placeholder={traduire("Ex. 5 000")}/>
        {action === "dette" && <Input label="Note (facultative)" value={note} onChange={(event) => setNote(event.target.value)} placeholder={traduire("Ex. Achat de marchandises")}/>}
        {action === "correction" && <Input label="Raison obligatoire" as="textarea" rows={3} maxLength={250} required value={raison} onChange={(event) => setRaison(event.target.value)} placeholder={traduire("Expliquez la correction")}/>}
        {erreur && <div className="alert-box" role="alert">{erreur}</div>}
        <div className="form-actions justify-end"><Button variant="secondary" onClick={fermer}>{<TexteLocalise phrase={"Annuler"} />}</Button><Button type="submit" disabled={envoi}>{envoi ? "Enregistrement…" : action === "dette" ? "Ajouter la dette" : action === "paiement" ? "Confirmer le paiement" : "Enregistrer la correction"}</Button></div>
      </form>
    </Modal>
  </>;
}
