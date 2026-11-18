import { useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminErreur, AdminTitre, formatDate } from "../AdminComponents";
import { TexteLocalise, traduire } from "../../contexte/LangueContext";

const MESSAGE_DEFAUT = "Une maintenance est en cours. Merci de revenir dans quelques instants.";

export default function AdminMaintenance() {
  const [actif, setActif] = useState(false);
  const [message, setMessage] = useState(MESSAGE_DEFAUT);
  const [modifieLe, setModifieLe] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState("");
  const [succes, setSucces] = useState("");

  useEffect(() => {
    adminApi.get("/api/admin/maintenance/")
      .then(({ data }) => {
        setActif(data.actif);
        setMessage(data.message || MESSAGE_DEFAUT);
        setModifieLe(data.modifie_le);
      })
      .catch((error) => setErreur(erreurAdmin(error)))
      .finally(() => setChargement(false));
  }, []);

  async function basculerMode() {
    const prochainEtat = !actif;
    if (prochainEtat && !window.confirm(traduire("Activer la maintenance ? Les opérations des commerçants seront temporairement bloquées. Le back-office restera accessible."))) return;
    setErreur("");
    setSucces("");
    setEnCours(true);
    try {
      const { data } = await adminApi.patch("/api/admin/maintenance/", { actif: prochainEtat, message: message.trim() });
      setActif(data.actif);
      setMessage(data.message);
      setModifieLe(data.modifie_le);
      setSucces(data.actif ? "Le mode maintenance est activé." : "Le mode maintenance est désactivé.");
    } catch (error) {
      setErreur(erreurAdmin(error));
    } finally {
      setEnCours(false);
    }
  }

  return <>
    <AdminTitre titre="Maintenance de l’application" description="Informez les utilisateurs et suspendez temporairement les opérations de l’espace commerçant."/>
    <AdminErreur>{erreur}</AdminErreur>
    {chargement ? <div className="admin-loading" aria-label={traduire("Chargement")}><i/><i/><i/></div> : <div className="admin-panel admin-maintenance-panel">
      <div className="admin-trial-status"><span>{<TexteLocalise phrase={"État actuel"} />}</span><AdminBadge tone={actif ? "red" : "green"}>{actif ? "Maintenance active" : "Application disponible"}</AdminBadge></div>
      <p className="admin-maintenance-description"><TexteLocalise phrase="Lorsqu’elle est active, les commerçants voient un écran de maintenance et les requêtes de gestion sont bloquées. Le back-office reste accessible pour désactiver le mode." /></p>
      <label className="admin-maintenance-label">{<TexteLocalise phrase={"Message affiché aux utilisateurs"} />}
        <textarea rows="3" maxLength="300" value={message} onChange={(event) => setMessage(event.target.value)} disabled={enCours}/>
        <small>{message.length}/300</small>
      </label>
      {succes && <p className="admin-success" role="status">{traduire(succes)}</p>}
      {modifieLe && <p className="admin-hint">{<TexteLocalise phrase={"Dernière modification :"} />}{' '}{formatDate(modifieLe, true)}</p>}
      <button className={`admin-button ${actif ? "admin-button-secondary" : "admin-button-primary"}`} type="button" disabled={enCours || !message.trim()} onClick={basculerMode}>
        {enCours ? <TexteLocalise phrase={"Mise à jour…"} /> : actif ? <TexteLocalise phrase={"Désactiver la maintenance"} /> : <TexteLocalise phrase={"Activer la maintenance"} />}
      </button>
    </div>}
  </>;
}
