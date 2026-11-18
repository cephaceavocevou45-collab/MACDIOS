import { useCallback, useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Modal from "../composants/Modal";
import Pagination from "../composants/Pagination";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { extraireListe } from "../utils";
import { TexteLocalise } from "../contexte/LangueContext";

const formulaireVide = { nom: "", telephone: "", email: "", adresse: "" };

export default function Fournisseurs() {
  const [fournisseurs, setFournisseurs] = useState([]);
  const [formulaire, setFormulaire] = useState(formulaireVide);
  const [recherche, setRecherche] = useState("");
  const [aArchiver, setAArchiver] = useState(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const notifier = useToast();

  const charger = useCallback(async () => {
    setChargement(true);
    try {
      const { data } = await api.get("/api/fournisseurs/", { params: { page, recherche: recherche || undefined } });
      setFournisseurs(extraireListe(data)); setTotal(data.count ?? extraireListe(data).length); setErreur("");
    } catch (error) { setErreur(messageErreur(error)); }
    finally { setChargement(false); }
  }, [page, recherche]);
  useEffect(() => { charger(); }, [charger]);

  async function enregistrer(event) {
    event.preventDefault(); setEnvoi(true); setErreur("");
    try {
      await api.post("/api/fournisseurs/", formulaire);
      setFormulaire(formulaireVide); notifier("Fournisseur ajouté."); await charger();
    } catch (error) { const message = messageErreur(error); setErreur(message); notifier(message, "error"); }
    finally { setEnvoi(false); }
  }

  async function archiver() {
    try { await api.delete(`/api/fournisseurs/${aArchiver.id}/`); notifier("Fournisseur archivé."); setAArchiver(null); await charger(); }
    catch (error) { const message = messageErreur(error); setErreur(message); notifier(message, "error"); setAArchiver(null); }
  }

  return <>
    <div className="page-heading"><div><span className="form-eyebrow"><TexteLocalise phrase="Achats et stock"/></span><h1><TexteLocalise phrase="Fournisseurs"/></h1><p><TexteLocalise phrase="Centralisez les contacts des entreprises qui approvisionnent votre boutique."/></p></div></div>
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <Card className="mb-5"><div className="section-card-heading"><div><h2><TexteLocalise phrase="Ajouter un fournisseur"/></h2><p><TexteLocalise phrase="Les coordonnées restent privées dans votre espace."/></p></div></div>
      <form className="form-grid" onSubmit={enregistrer}>
        <Input label="Nom du fournisseur" required maxLength={160} value={formulaire.nom} onChange={(event) => setFormulaire({ ...formulaire, nom: event.target.value })}/>
        <Input label="Téléphone" type="tel" maxLength={32} value={formulaire.telephone} onChange={(event) => setFormulaire({ ...formulaire, telephone: event.target.value })}/>
        <Input label="Adresse email" type="email" maxLength={254} value={formulaire.email} onChange={(event) => setFormulaire({ ...formulaire, email: event.target.value })}/>
        <Input label="Adresse" maxLength={250} value={formulaire.adresse} onChange={(event) => setFormulaire({ ...formulaire, adresse: event.target.value })}/>
        <div className="form-actions col-span-full"><Button type="submit" disabled={envoi}>{envoi ? <TexteLocalise phrase="Enregistrement…"/> : <><Icon name="plus" size={17}/><TexteLocalise phrase="Ajouter le fournisseur"/></>}</Button></div>
      </form>
    </Card>
    <div className="filter-row"><div><h2 className="m-0 text-lg font-semibold"><TexteLocalise phrase="Vos fournisseurs"/></h2><p className="mt-1 text-sm text-ink-muted">{total} <TexteLocalise phrase="fournisseur(s)"/></p></div><input className="field-control max-w-sm" type="search" placeholder="Rechercher un fournisseur" value={recherche} onChange={(event) => { setRecherche(event.target.value); setPage(1); }}/></div>
    {chargement ? <div className="product-card-grid">{[1, 2, 3].map((n) => <SkeletonCard key={n}/>)}</div> : fournisseurs.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="users" size={24}/></span><h3><TexteLocalise phrase="Aucun fournisseur pour le moment"/></h3><p><TexteLocalise phrase="Ajoutez un fournisseur avant d’enregistrer votre prochaine réception de marchandises."/></p></Card> :
      <div className="product-card-grid">{fournisseurs.map((fournisseur) => <Card key={fournisseur.id} className="product-item-card"><div className="product-item-top"><span className="product-icon"><Icon name="users" size={20}/></span><span className="text-xs text-ink-muted">#{fournisseur.id}</span></div><h3>{fournisseur.nom}</h3>{fournisseur.telephone && <p className="mb-1 text-sm text-ink-muted">{fournisseur.telephone}</p>}{fournisseur.email && <p className="mb-1 truncate text-sm text-ink-muted">{fournisseur.email}</p>}{fournisseur.adresse && <p className="mb-3 text-sm text-ink-muted">{fournisseur.adresse}</p>}<div className="product-actions"><Button variant="danger" size="small" onClick={() => setAArchiver(fournisseur)}><TexteLocalise phrase="Archiver"/></Button></div></Card>)}</div>}
    <Pagination page={page} count={total} onChange={setPage}/>
    <Modal open={Boolean(aArchiver)} title="Archiver ce fournisseur ?" onClose={() => setAArchiver(null)}>{aArchiver && <><p className="mb-5 text-sm text-ink-muted"><TexteLocalise phrase="Les réceptions passées seront conservées."/></p><div className="form-actions justify-end"><Button variant="secondary" onClick={() => setAArchiver(null)}><TexteLocalise phrase="Annuler"/></Button><Button variant="danger" onClick={archiver}><TexteLocalise phrase="Archiver"/></Button></div></>}</Modal>
  </>;
}
