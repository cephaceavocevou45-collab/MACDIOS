import { useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminErreur, AdminTitre, formatDate } from "../AdminComponents";

export default function AdminOffreEssai() {
  const [actif, setActif] = useState(true);
  const [duree, setDuree] = useState("14");
  const [modifieLe, setModifieLe] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState("");
  const [succes, setSucces] = useState("");

  useEffect(() => {
    adminApi.get("/api/admin/offre-essai/")
      .then(({ data }) => { setActif(data.actif); setDuree(String(data.duree_jours)); setModifieLe(data.modifie_le); })
      .catch((error) => setErreur(erreurAdmin(error)))
      .finally(() => setChargement(false));
  }, []);

  async function enregistrer(event) {
    event.preventDefault();
    setErreur(""); setSucces(""); setEnCours(true);
    try {
      const { data } = await adminApi.patch("/api/admin/offre-essai/", { actif, duree_jours: Number(duree) });
      setActif(data.actif); setDuree(String(data.duree_jours)); setModifieLe(data.modifie_le);
      setSucces("L’offre gratuite a été mise à jour.");
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setEnCours(false); }
  }

  return <>
    <AdminTitre titre="Offre d’essai gratuite" description="Modifiez la durée de l’essai ou désactivez-le pour les nouvelles inscriptions."/>
    <AdminErreur>{erreur}</AdminErreur>
    {chargement ? <div className="admin-loading" aria-label="Chargement"><i/><i/><i/></div> : <div className="admin-panel admin-trial-panel">
      <div className="admin-trial-status"><span>État actuel</span><AdminBadge tone={actif ? "green" : "red"}>{actif ? "Essai proposé" : "Essai désactivé"}</AdminBadge></div>
      <form className="admin-form" onSubmit={enregistrer}>
        <label className="admin-toggle-row"><span><strong>Proposer l’essai gratuit</strong><small>Ce réglage s’applique aux nouveaux comptes. Les essais déjà attribués ne changent pas.</small></span><input type="checkbox" checked={actif} onChange={(event) => setActif(event.target.checked)}/></label>
        <label>Durée de l’essai, en jours<input type="number" min="1" max="365" required value={duree} onChange={(event) => setDuree(event.target.value)} disabled={!actif}/><small>Choisissez une durée entre 1 et 365 jours.</small></label>
        {succes && <p className="admin-success" role="status">{succes}</p>}
        {modifieLe && <p className="admin-hint">Dernière modification : {formatDate(modifieLe, true)}</p>}
        <button className="admin-button admin-button-primary" disabled={enCours}>{enCours ? "Enregistrement…" : "Enregistrer les réglages"}</button>
      </form>
    </div>}
  </>;
}
