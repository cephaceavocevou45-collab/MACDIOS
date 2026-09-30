import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { Chargement, Erreur } from "../composants/Commun";
import { useToast } from "../composants/ToastProvider";

const fcfa = (montant) => `${Number(montant || 0).toLocaleString("fr-FR")} FCFA`;

export default function Abonnement() {
  const [abonnement, setAbonnement] = useState(null);
  const [plans, setPlans] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [demandes, setDemandes] = useState([]);
  const [planChoisi, setPlanChoisi] = useState(null);
  const [operateurChoisi, setOperateurChoisi] = useState("");
  const [referenceManuelle, setReferenceManuelle] = useState("");
  const [preuve, setPreuve] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [planEnCours, setPlanEnCours] = useState(null);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();
  const demandeEnAttente = demandes.some((demande) => demande.statut === "en_attente");

  const charger = useCallback(async () => {
    const [etat, offres, historique] = await Promise.all([
      api.get("/api/abonnement/"),
      api.get("/api/plans/"),
      api.get("/api/abonnement/transactions/"),
    ]);
    const demandesManuelles = etat.data.mode_paiement === "manuel"
      ? await api.get("/api/abonnement/demandes/")
      : { data: [] };
    setAbonnement(etat.data);
    setPlans(offres.data);
    setTransactions(historique.data);
    setDemandes(demandesManuelles.data);
  }, []);

  useEffect(() => {
    charger().catch((e) => setErreur(messageErreur(e))).finally(() => setChargement(false));
  }, [charger]);

  function commencerPaiement(plan) {
    setPlanChoisi(plan);
    setOperateurChoisi("");
    setErreur("");
  }

  async function envoyerDemande(event) {
    event.preventDefault();
    if (!planChoisi) return;
    setPlanEnCours(planChoisi.id);
    setErreur("");
    try {
      const contenu = new FormData();
      contenu.append("plan", String(planChoisi.id));
      contenu.append("operateur", operateurChoisi);
      contenu.append("reference_transaction", referenceManuelle.trim());
      if (preuve) contenu.append("preuve", preuve);
      await api.post("/api/abonnement/demandes/", contenu, { headers: { "Content-Type": "multipart/form-data" } });
      setReferenceManuelle("");
      setPreuve(null);
      setPlanChoisi(null);
      setOperateurChoisi("");
      await charger();
      notifier("Demande reçue. Elle sera vérifiée par notre équipe.", "success");
    } catch (e) {
      const message = messageErreur(e);
      setErreur(message);
      notifier(message, "error");
    } finally {
      setPlanEnCours(null);
    }
  }

  async function telechargerRecu(demande) {
    try {
      const { data } = await api.get(`/api/abonnement/demandes/${demande.id}/recu/`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = `recu-abonnement-${demande.id}.pdf`;
      lien.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifier(messageErreur(e), "error");
    }
  }

  if (chargement) return <Chargement texte="Chargement de votre abonnement…"/>;

  return (
    <div className="page-stack">
      <div className="page-heading-row">
        <div><span className="eyebrow">Mon compte</span><h1 className="workspace-title">Abonnement</h1><p className="workspace-subtitle">Consultez votre accès et choisissez une formule.</p></div>
      </div>
      <Erreur texte={erreur}/>

      {abonnement && <Card className="subscription-current">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="mb-2 text-sm font-semibold text-ink-muted">Votre formule actuelle</p><h2 className="m-0 text-2xl font-bold">{abonnement.plan.nom}</h2></div>
          <Badge tone={abonnement.statut === "actif" ? "green" : abonnement.statut === "essai" ? "orange" : "red"}>{abonnement.statut === "essai" ? "Période d’essai" : abonnement.statut === "actif" ? "Actif" : "Expiré"}</Badge>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="subscription-detail"><Icon name="clock"/><span>Jours restants</span><strong>{abonnement.jours_restants}</strong></div>
          <div className="subscription-detail"><Icon name="subscription"/><span>Valable jusqu’au</span><strong>{new Date(abonnement.date_fin).toLocaleDateString("fr-FR")}</strong></div>
        </div>
        {abonnement.statut === "expire" && <p className="mt-4 mb-0 text-sm font-medium text-red-700">Votre espace est en lecture seule jusqu’à la réactivation de l’abonnement.</p>}
      </Card>}

      <section className="page-stack">
        <div><h2 className="m-0 text-xl font-bold">Choisir une formule</h2><p className="mt-1 text-sm text-ink-muted">Paiement Mobile Money avec vérification par notre équipe.</p></div>
        {demandeEnAttente && <Card><p className="m-0 text-sm font-semibold text-amber-800">Une demande de paiement est déjà en attente de vérification. Vous pourrez choisir une nouvelle formule après son traitement.</p></Card>}
        {plans.length === 0 ? <Card><p className="m-0 text-ink-muted">Aucune formule payante n’est disponible pour le moment.</p></Card> :
          <div className="grid gap-4 md:grid-cols-2">{plans.map((plan) => <Card key={plan.id} className="subscription-plan">
            <div className="flex items-center justify-between gap-3"><h3 className="m-0 text-lg font-bold">{plan.nom}</h3><Icon name="spark" className="text-brand"/></div>
            <p className="my-4 text-3xl font-bold tracking-tight">{fcfa(plan.prix)}<span className="ml-1 text-sm font-medium text-ink-muted">/ {plan.duree_jours} jours</span></p>
            <Button className="w-full" disabled={planEnCours !== null || demandeEnAttente} onClick={() => commencerPaiement(plan)}>
              <><Icon name="wallet"/>Choisir cette formule</>
            </Button>
          </Card>)}</div>}
      </section>

      {planChoisi && <Card>
        <h2 className="m-0 text-xl font-bold">Payer {planChoisi.nom} par Mobile Money</h2>
        {!(abonnement.operateurs_paiement || []).length ? <div className="my-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950" role="status">
          <strong>Le paiement Mobile Money n’est pas configuré sur le serveur.</strong>
          <p className="mb-0 mt-1">Aucun numéro d’opérateur n’a été transmis par le backend. Vérifiez les variables NUMERO_MTN, NUMERO_MOOV ou NUMERO_CELTIIS dans le fichier .env du backend, puis redémarrez Django. Ne faites pas de transfert avant que le numéro du bénéficiaire s’affiche ici.</p>
        </div> : <>
        <div className="my-4 rounded-xl bg-brand/5 p-4 text-base leading-7">
          <p className="m-0">1. Choisissez l’opérateur utilisé pour votre transfert. Le numéro s’affichera après votre choix.</p>
        </div>
        <fieldset className="mb-4 grid gap-3 border-0 p-0 sm:grid-cols-3">
          <legend className="mb-2 text-sm font-semibold">Votre opérateur Mobile Money</legend>
          {(abonnement.operateurs_paiement || []).map((operateur) => <label key={operateur.code} className={`cursor-pointer rounded-xl border p-4 ${operateurChoisi === operateur.code ? "border-brand bg-brand/5" : "border-line bg-white"}`}>
            <span className="flex items-center gap-2 font-bold"><input type="radio" name="operateur" value={operateur.code} checked={operateurChoisi === operateur.code} onChange={() => setOperateurChoisi(operateur.code)}/>{operateur.nom}</span>
          </label>)}
        </fieldset>
        {operateurChoisi && (() => {
          const operateur = abonnement.operateurs_paiement.find((item) => item.code === operateurChoisi);
          return operateur ? <>
            <div className="my-4 rounded-xl bg-brand/5 p-4 text-base leading-7">
              <p className="m-0">2. Transférez exactement <strong>{fcfa(planChoisi.prix)}</strong> via {operateur.nom} au numéro :</p>
              <p className="my-2 text-2xl font-bold tracking-wide">{operateur.numero}</p>
              <p className="m-0">3. Recopiez la référence reçue par SMS. Vous pourrez joindre une capture d’écran du transfert.</p>
            </div>
            <form className="grid gap-4" onSubmit={envoyerDemande}>
              <label className="grid gap-2 text-sm font-semibold">Référence du transfert
                <input className="field-control" value={referenceManuelle} onChange={(event) => setReferenceManuelle(event.target.value)} required maxLength={120} />
              </label>
              <label className="grid gap-2 text-sm font-semibold">Capture d’écran (facultative, 5 Mo maximum)
                <input className="field-control" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPreuve(event.target.files?.[0] || null)} />
              </label>
              <div className="flex flex-wrap gap-3"><Button type="submit" disabled={planEnCours !== null || !operateurChoisi}>{planEnCours ? "Envoi…" : "J’ai payé"}</Button><Button type="button" variant="secondary" onClick={() => { setPlanChoisi(null); setOperateurChoisi(""); }}>Annuler</Button></div>
            </form>
          </> : null;
        })()}
        </>}
      </Card>}
      {demandes.length > 0 && <section className="page-stack">
        <div><h2 className="m-0 text-xl font-bold">Mes demandes de paiement</h2><p className="mt-1 text-sm text-ink-muted">Une demande en attente bloque un nouvel envoi.</p></div>
        {demandes.map((demande) => <Card key={demande.id} className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
          <div><strong>{demande.plan_nom} · {fcfa(demande.montant)}</strong><p className="m-0 mt-1 text-sm text-ink-muted">{demande.operateur_nom || demande.operateur || "Opérateur non renseigné"} · Demande du {new Date(demande.date_demande).toLocaleString("fr-FR")}</p>
            {demande.statut === "en_attente" && <p className="m-0 mt-2 font-semibold text-amber-700">En attente de vérification. Vous serez notifié dès que votre paiement sera validé.</p>}
            {demande.statut === "rejetee" && <p className="m-0 mt-2 text-red-700">Demande rejetée : {demande.motif_rejet}</p>}
            {demande.statut === "validee" && <p className="m-0 mt-2 font-semibold text-emerald-700">Paiement vérifié, votre abonnement est actif jusqu’au {new Date(abonnement.date_fin).toLocaleDateString("fr-FR")}.</p>}
          </div>
          <div className="flex items-center gap-3"><Badge tone={demande.statut === "validee" ? "green" : demande.statut === "rejetee" ? "red" : "orange"}>{demande.statut === "validee" ? "Validée" : demande.statut === "rejetee" ? "Rejetée" : "En attente"}</Badge>{demande.statut === "validee" && <Button onClick={() => telechargerRecu(demande)}>Télécharger le reçu (PDF)</Button>}</div>
        </Card>)}
      </section>}

      <section className="page-stack">
        <div><h2 className="m-0 text-xl font-bold">Historique des paiements</h2><p className="mt-1 text-sm text-ink-muted">État des paiements liés à votre compte.</p></div>
        {transactions.length === 0 ? <Card><p className="m-0 text-ink-muted">Aucun paiement enregistré.</p></Card> :
          <div className="grid gap-3">{transactions.map((transaction) => <Card key={transaction.reference} className="subscription-history-row">
            <div><strong>{transaction.plan_nom}</strong><small>{new Date(transaction.date_creation).toLocaleString("fr-FR")}</small></div>
            <strong>{fcfa(transaction.montant)}</strong>
            <Badge tone={transaction.statut === "reussi" ? "green" : transaction.statut === "echoue" ? "red" : "orange"}>{transaction.statut === "reussi" ? "Réussi" : transaction.statut === "echoue" ? "Échoué" : "En attente"}</Badge>
          </Card>)}</div>}
      </section>
      <Link className="btn-ghost w-fit" to="/tableau-de-bord"><Icon name="arrow"/>Retour au tableau de bord</Link>
    </div>
  );
}
