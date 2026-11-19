import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { Chargement, Erreur } from "../composants/Commun";
import { useToast } from "../composants/ToastProvider";
import Pagination from "../composants/Pagination";
import { extraireListe } from "../utils";
import { localePourLangue, TexteLocalise, useLangue } from "../contexte/LangueContext";

export default function Abonnement() {
  const { langue } = useLangue();
  const [searchParams, setSearchParams] = useSearchParams();
  const fcfa = (montant) => `${Number(montant || 0).toLocaleString(localePourLangue(langue))} FCFA`;
  const dateLocale = (valeur, avecHeure = false) => new Intl.DateTimeFormat(
    localePourLangue(langue), avecHeure ? { dateStyle: "short", timeStyle: "short" } : { dateStyle: "medium" },
  ).format(new Date(valeur));
  const [abonnement, setAbonnement] = useState(null);
  const [plans, setPlans] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [planChoisi, setPlanChoisi] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [planEnCours, setPlanEnCours] = useState(null);
  const [erreur, setErreur] = useState("");
  const [planPage, setPlanPage] = useState(1);
  const [transactionPage, setTransactionPage] = useState(1);
  const [nombrePlans, setNombrePlans] = useState(0);
  const [nombreTransactions, setNombreTransactions] = useState(0);
  const notifier = useToast();

  const charger = useCallback(async () => {
    const [etat, offres, historique] = await Promise.all([
      api.get("/api/abonnement/"),
      api.get("/api/plans/", { params: { page: planPage } }),
      api.get("/api/abonnement/transactions/", { params: { page: transactionPage } }),
    ]);
    setAbonnement(etat.data);
    setPlans(extraireListe(offres.data));
    setNombrePlans(offres.data.count ?? extraireListe(offres.data).length);
    setTransactions(extraireListe(historique.data));
    setNombreTransactions(historique.data.count ?? extraireListe(historique.data).length);
  }, [planPage, transactionPage]);

  useEffect(() => {
    charger().catch((e) => setErreur(messageErreur(e))).finally(() => setChargement(false));
  }, [charger]);

  useEffect(() => {
    const reference = searchParams.get("paiement");
    if (!reference) return;
    api.get(`/api/abonnement/paiements/${reference}/`)
      .then(({ data }) => {
        if (data.statut === "reussi") notifier("Paiement confirmé. Votre abonnement est actif.", "success");
        else if (data.statut === "echoue") notifier("Le paiement n’a pas abouti. Vous pouvez réessayer.", "error");
        else notifier("Paiement en cours de confirmation. Revenez dans un instant.", "info");
        return charger();
      })
      .catch((e) => notifier(messageErreur(e), "error"))
      .finally(() => setSearchParams({}, { replace: true }));
  }, [searchParams, setSearchParams, charger, notifier]);

  function commencerPaiement(plan) {
    setPlanChoisi(plan);
    setErreur("");
  }

  async function envoyerDemande() {
    if (!planChoisi) return;
    setPlanEnCours(planChoisi.id);
    setErreur("");
    try {
      const { data } = await api.post("/api/abonnement/paiements/", { plan_id: planChoisi.id });
      window.location.assign(data.checkout_url);
    } catch (e) {
      const message = messageErreur(e);
      setErreur(message);
      notifier(message, "error");
    } finally {
      setPlanEnCours(null);
    }
  }

  async function verifierPaiement(reference) {
    try {
      const { data } = await api.get(`/api/abonnement/paiements/${reference}/`);
      await charger();
      notifier(data.statut === "reussi" ? "Paiement confirmé. Votre abonnement est actif." : data.statut === "echoue" ? "Le paiement n’a pas abouti." : "Le paiement est toujours en cours de confirmation.", data.statut === "reussi" ? "success" : "info");
    } catch (e) { notifier(messageErreur(e), "error"); }
  }

  if (chargement) return <Chargement texte="Chargement de votre abonnement…"/>;

  return (
    <div className="page-stack">
      <div className="page-heading-row">
        <div><span className="eyebrow">{<TexteLocalise phrase={"Mon compte"} />}</span><h1 className="workspace-title">{<TexteLocalise phrase={"Abonnement"} />}</h1><p className="workspace-subtitle">{<TexteLocalise phrase={"Consultez votre accès et choisissez une formule."} />}</p></div>
      </div>
      <Erreur texte={erreur}/>

      {abonnement && <Card className="subscription-current">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="mb-2 text-sm font-semibold text-ink-muted">{<TexteLocalise phrase={"Votre formule actuelle"} />}</p><h2 className="m-0 text-2xl font-bold">{abonnement.plan.nom}</h2></div>
          <Badge tone={abonnement.statut === "actif" ? "green" : abonnement.statut === "essai" ? "orange" : "red"}>{abonnement.statut === "essai" ? "Période d’essai" : abonnement.statut === "actif" ? "Actif" : "Expiré"}</Badge>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="subscription-detail"><Icon name="clock"/><span>{<TexteLocalise phrase={"Jours restants"} />}</span><strong>{abonnement.jours_restants}</strong></div>
          <div className="subscription-detail"><Icon name="subscription"/><span>{<TexteLocalise phrase={"Valable jusqu’au"} />}</span><strong>{dateLocale(abonnement.date_fin)}</strong></div>
        </div>
        {abonnement.statut === "expire" && <p className="mt-4 mb-0 text-sm font-medium text-red-700">{<TexteLocalise phrase={"Votre espace est en lecture seule jusqu’à la réactivation de l’abonnement."} />}</p>}
      </Card>}

      <section className="page-stack">
        <div><h2 className="m-0 text-xl font-bold">{<TexteLocalise phrase={"Choisir une formule"} />}</h2><p className="mt-1 text-sm text-ink-muted">Paiement sécurisé par FedaPay (Mobile Money et moyens disponibles selon votre compte).</p></div>
        {plans.length === 0 ? <Card><p className="m-0 text-ink-muted">{<TexteLocalise phrase={"Aucune formule payante n’est disponible pour le moment."} />}</p></Card> :
          <div className="grid gap-4 md:grid-cols-2">{plans.map((plan) => <Card key={plan.id} className="subscription-plan">
            <div className="flex items-center justify-between gap-3"><h3 className="m-0 text-lg font-bold">{plan.nom}</h3><Icon name="spark" className="text-brand"/></div>
            <p className="my-4 text-3xl font-bold tracking-tight">{fcfa(plan.prix)}<span className="ml-1 text-sm font-medium text-ink-muted">/ {plan.duree_jours}{' '}{<TexteLocalise phrase={"jours"} />}</span></p>
            <Button className="w-full" disabled={planEnCours !== null} onClick={() => commencerPaiement(plan)}>
              <><Icon name="wallet"/>{<TexteLocalise phrase={"Choisir cette formule"} />}</>
            </Button>
          </Card>)}</div>}
        <Pagination page={planPage} count={nombrePlans} onChange={setPlanPage}/>
      </section>

      {planChoisi && <Card>
        <p className="my-4 text-ink-muted">Vous allez être redirigé vers FedaPay pour régler {fcfa(planChoisi.prix)}. L’abonnement s’active après confirmation du paiement.</p>
        <div className="flex flex-wrap gap-3"><Button disabled={planEnCours !== null} onClick={envoyerDemande}>{planEnCours ? "Ouverture de FedaPay…" : "Continuer vers FedaPay"}</Button><Button variant="secondary" onClick={() => setPlanChoisi(null)}>Annuler</Button></div>
      </Card>}

      <section className="page-stack">
        <div><h2 className="m-0 text-xl font-bold">{<TexteLocalise phrase={"Historique des paiements"} />}</h2><p className="mt-1 text-sm text-ink-muted">{<TexteLocalise phrase={"État des paiements liés à votre compte."} />}</p></div>
        {transactions.length === 0 ? <Card><p className="m-0 text-ink-muted">{<TexteLocalise phrase={"Aucun paiement enregistré."} />}</p></Card> :
          <div className="grid gap-3">{transactions.map((transaction) => <Card key={transaction.reference} className="subscription-history-row">
            <div><strong>{transaction.plan_nom}</strong><small>{dateLocale(transaction.date_creation, true)}</small></div>
            <strong>{fcfa(transaction.montant)}</strong>
            <Badge tone={transaction.statut === "reussi" ? "green" : transaction.statut === "echoue" ? "red" : "orange"}>{transaction.statut === "reussi" ? "Réussi" : transaction.statut === "echoue" ? "Échoué" : "En attente"}</Badge>
            {transaction.statut === "en_attente" && <Button variant="secondary" onClick={() => verifierPaiement(transaction.reference)}>Vérifier l’état</Button>}
          </Card>)}</div>}
        <Pagination page={transactionPage} count={nombreTransactions} onChange={setTransactionPage}/>
      </section>
      <Link className="btn-ghost w-fit" to="/tableau-de-bord"><Icon name="arrow"/>{<TexteLocalise phrase={"Retour au tableau de bord"} />}</Link>
    </div>
  );
}
