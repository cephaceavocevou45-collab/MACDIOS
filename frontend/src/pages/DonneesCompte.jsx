import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Modal from "../composants/Modal";
import { useToast } from "../composants/ToastProvider";
import { useAuth } from "../contexte/AuthContext";

export default function DonneesCompte() {
  const [confirmation, setConfirmation] = useState(false);
  const [motDePasse, setMotDePasse] = useState("");
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();
  const { deconnexion } = useAuth();
  const naviguer = useNavigate();

  async function exporter() {
    setChargement(true);
    try {
      const { data } = await api.get("/api/compte/export/", { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = "mes-donnees-commerce.pdf";
      lien.click();
      URL.revokeObjectURL(url);
      notifier("Votre export PDF a été téléchargé.");
    } catch (error) {
      const texte = messageErreur(error);
      setErreur(texte);
      notifier(texte, "error");
    } finally {
      setChargement(false);
    }
  }

  async function supprimer(event) {
    event.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      await api.delete("/api/compte/", { data: { mot_de_passe: motDePasse } });
      deconnexion();
      naviguer("/", { replace: true });
    } catch (error) {
      setErreur(messageErreur(error));
    } finally {
      setChargement(false);
    }
  }

  return <div className="page-stack">
    <div className="page-heading"><div><span className="form-eyebrow">Confidentialité</span><h1>Mes données et mon compte</h1><p>Téléchargez une copie de vos données ou demandez la suppression définitive du compte.</p></div></div>
    {erreur && <div className="alert-box" role="alert">{erreur}</div>}
    <Card><div className="section-card-heading"><div><h2>Exporter mes données</h2><p>Téléchargez un document PDF lisible avec les données de votre boutique.</p></div><span className="feature-icon"><Icon name="box"/></span></div><Button disabled={chargement} onClick={exporter}>Exporter mes données (PDF)</Button></Card>
    <Card><div className="section-card-heading"><div><h2>Supprimer mon compte</h2><p>Cette action efface votre compte, vos données métier et votre historique d&apos;activité. Elle est définitive.</p></div><span className="feature-icon"><Icon name="info"/></span></div><Button variant="danger" onClick={() => { setErreur(""); setMotDePasse(""); setConfirmation(true); }}>Supprimer mon compte</Button></Card>
    <Modal open={confirmation} title="Confirmer la suppression" onClose={() => setConfirmation(false)}><form className="grid gap-4" onSubmit={supprimer}><p className="m-0 text-sm leading-6 text-ink-muted">Saisissez votre mot de passe pour confirmer l&apos;effacement définitif de toutes les données de votre boutique.</p><Input label="Mot de passe" type="password" autoComplete="current-password" required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)}/>{erreur && <div className="alert-box" role="alert">{erreur}</div>}<div className="form-actions justify-end"><Button variant="secondary" type="button" onClick={() => setConfirmation(false)}>Annuler</Button><Button variant="danger" type="submit" disabled={chargement}>{chargement ? "Suppression…" : "Confirmer la suppression"}</Button></div></form></Modal>
  </div>;
}
