import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import Icon from "./Icon";

export default function AlerteAbonnement() {
  const [abonnement, setAbonnement] = useState(null);

  useEffect(() => {
    let actif = true;
    api.get("/api/abonnement/")
      .then(({ data }) => { if (actif) setAbonnement(data); })
      .catch(() => {});
    return () => { actif = false; };
  }, []);

  if (!abonnement) return null;
  const expire = abonnement.statut === "expire";
  const essai = abonnement.statut === "essai";
  if (!expire && !essai) return null;

  return (
    <div className={`subscription-alert ${expire ? "expired" : "trial"}`} role="status">
      <Icon name={expire ? "info" : "clock"} size={19}/>
      <p>{expire ? "Abonnement expiré. Vos données restent consultables." : `Il vous reste ${abonnement.jours_restants} jour${abonnement.jours_restants === 1 ? "" : "s"} d’essai.`}</p>
      <Link to="/abonnement">{expire ? "Réactiver" : "Voir l’offre"}<span aria-hidden="true"> →</span></Link>
    </div>
  );
}
