import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { Chargement, Erreur } from "../composants/Commun";
import { useToast } from "../composants/ToastProvider";

const FCFA = (valeur) => `${Number(valeur || 0).toLocaleString("fr-FR")} FCFA`;

export default function ReclamationPaiement() {
  const { reference } = useParams();
  const notifier = useToast();
  const [paiement, setPaiement] = useState(null);
  const [description, setDescription] = useState("");
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    let vivant = true;
    api.get(`/api/abonnement/paiements/${reference}/`)
      .then(({ data }) => { if (vivant) setPaiement(data); })
      .catch((e) => { if (vivant) setErreur(messageErreur(e)); })
      .finally(() => { if (vivant) setChargement(false); });
    return () => { vivant = false; };
  }, [reference]);

  async function envoyer(e) {
    e.preventDefault();
    setEnvoi(true);
    setErreur("");
    try {
      await api.post(`/api/abonnement/paiements/${reference}/reclamation/`, { description });
      setPaiement((actuel) => ({ ...actuel, reclamation_deja_envoyee: true }));
      notifier("Votre signalement a été transmis à l’équipe MACDIOS.", "success");
    } catch (e2) { setErreur(messageErreur(e2)); }
    finally { setEnvoi(false); }
  }

  if (chargement) return <Chargement texte="Chargement du paiement…"/>;
  return <main className="mx-auto w-full max-w-2xl page-stack px-4 py-8">
    <div><span className="eyebrow">Abonnement</span><h1 className="workspace-title">Signaler un problème de paiement</h1><p className="workspace-subtitle">Votre retour aide l’équipe à comprendre les difficultés rencontrées avec FedaPay.</p></div>
    <Erreur texte={erreur}/>
    {paiement && <Card>
      <p className="m-0"><strong>{paiement.plan_nom}</strong> · {FCFA(paiement.montant)}</p>
      <small className="mt-2 block text-ink-muted">Référence : {paiement.reference}</small>
      {paiement.reclamation_deja_envoyee ? <div className="mt-5" role="status"><h2 className="text-lg font-bold">Signalement reçu</h2><p className="text-ink-muted">Merci {paiement.nom_boutique}. L’équipe MACDIOS a reçu votre signalement et pourra examiner ce qui a bloqué le paiement.</p></div>
        : ["annule", "echoue"].includes(paiement.statut) ? <form className="mt-5 space-y-4" onSubmit={envoyer}>
          <label className="form-field"><span>Que s’est-il passé ?</span><textarea required minLength={10} maxLength={2000} rows={6} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Décrivez l’étape qui n’a pas fonctionné…"/><small>{description.length}/2 000 caractères (10 minimum).</small></label>
          <Button type="submit" disabled={envoi || description.trim().length < 10}>{envoi ? "Envoi…" : <><Icon name="send"/> Envoyer le signalement</>}</Button>
        </form> : <p className="mt-5 text-ink-muted">Ce paiement n’est pas annulé ni échoué. Vous pouvez vérifier son état depuis votre abonnement.</p>}
    </Card>}
    <Link className="btn-ghost w-fit" to="/abonnement"><Icon name="arrow"/> Retour à l’abonnement</Link>
  </main>;
}
