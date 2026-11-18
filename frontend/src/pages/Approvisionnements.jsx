import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import { TexteLocalise, traduire } from "../contexte/LangueContext";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Pagination from "../composants/Pagination";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";

const ligneVide = () => ({ produit: "", quantite: "1", prix_achat_unitaire: "" });

/** Enregistre une réception réelle : le backend augmente le stock atomiquement. */
export default function Approvisionnements() {
  const [produits, setProduits] = useState([]);
  const [fournisseurs, setFournisseurs] = useState([]);
  const [receptions, setReceptions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");
  const [formulaire, setFormulaire] = useState({ fournisseur: "", reference: "", note: "", lignes: [ligneVide()] });
  const [rechercheProduit, setRechercheProduit] = useState("");
  const [rechercheFournisseur, setRechercheFournisseur] = useState("");
  const notifier = useToast();

  const charger = useCallback(async () => {
    setChargement(true);
    try {
      const r = await api.get("/api/approvisionnements/", { params: { page } });
      setReceptions(extraireListe(r.data)); setTotal(r.data.count ?? extraireListe(r.data).length);
      setErreur("");
    } catch (error) { setErreur(`${traduire("Impossible de charger l’historique des réceptions.")} ${messageErreur(error)}`); }
    finally { setChargement(false); }
  }, [page]);
  useEffect(() => { charger(); }, [charger]);

  // Recherche serveur, afin de ne pas charger tout le catalogue des grandes boutiques.
  useEffect(() => {
    const controleur = new AbortController();
    const minuterie = window.setTimeout(async () => {
      try {
        const paramsF = rechercheFournisseur.trim() ? { recherche: rechercheFournisseur.trim() } : { page: 1 };
        const paramsP = rechercheProduit.trim() ? { recherche: rechercheProduit.trim() } : { page: 1 };
        const [f, p] = await Promise.all([
          api.get("/api/fournisseurs/", { params: paramsF, signal: controleur.signal }),
          api.get("/api/produits/", { params: paramsP, signal: controleur.signal }),
        ]);
        setFournisseurs((ancien) => [...new Map([...ancien, ...extraireListe(f.data)].map((item) => [item.id, item])).values()]);
        setProduits((ancien) => [...new Map([...ancien, ...extraireListe(p.data)].map((item) => [item.id, item])).values()]);
      } catch (error) {
        if (error.name !== "CanceledError" && error.code !== "ERR_CANCELED") {
          setErreur(`${traduire("Impossible de charger les fournisseurs et les produits.")} ${messageErreur(error)}`);
        }
      }
    }, 250);
    return () => { window.clearTimeout(minuterie); controleur.abort(); };
  }, [rechercheFournisseur, rechercheProduit]);

  function changerLigne(index, cle, valeur) {
    setFormulaire((ancien) => ({ ...ancien, lignes: ancien.lignes.map((ligne, i) => i === index ? { ...ligne, [cle]: valeur } : ligne) }));
  }

  async function enregistrer(event) {
    event.preventDefault(); setErreur(""); setEnvoi(true);
    const idsProduits = formulaire.lignes.map((ligne) => ligne.produit).filter(Boolean);
    if (idsProduits.length !== formulaire.lignes.length || new Set(idsProduits).size !== idsProduits.length) {
      setErreur(traduire("Choisissez un produit différent pour chaque ligne de réception.")); setEnvoi(false); return;
    }
    const lignes = formulaire.lignes.map((ligne) => ({ ...ligne, produit: Number(ligne.produit), quantite: Number(ligne.quantite), prix_achat_unitaire: Number(ligne.prix_achat_unitaire) }));
    try {
      await api.post("/api/approvisionnements/", { ...formulaire, fournisseur: formulaire.fournisseur ? Number(formulaire.fournisseur) : null, lignes });
      notifier("Réception enregistrée. Les quantités du stock ont été mises à jour.");
      setFormulaire({ fournisseur: "", reference: "", note: "", lignes: [ligneVide()] });
      setPage(1); await charger();
    } catch (error) {
      const message = `${traduire("Impossible d’enregistrer cette réception.")} ${messageErreur(error)}`;
      setErreur(message); notifier(message, "error");
    }
    finally { setEnvoi(false); }
  }

  return <>
    <div className="page-heading"><div><span className="form-eyebrow"><TexteLocalise phrase="Achats et stock"/></span><h1><TexteLocalise phrase="Réception de marchandises"/></h1><p><TexteLocalise phrase="Enregistrez les achats reçus pour augmenter le stock et actualiser le coût d’achat des produits."/></p></div><Link className="btn-secondary" to="/mouvements-stock"><Icon name="clock" size={17}/><TexteLocalise phrase="Mouvements de stock"/></Link></div>
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <Card className="mb-6"><div className="section-card-heading"><div><h2><TexteLocalise phrase="Nouvelle réception"/></h2><p><TexteLocalise phrase="Une réception confirmée ne peut pas être appliquée deux fois au stock."/></p></div></div>
      <form className="space-y-5" onSubmit={enregistrer}>
        <div className="form-grid">
          <div className="space-y-2"><Input label="Rechercher un fournisseur" value={rechercheFournisseur} onChange={(e) => setRechercheFournisseur(e.target.value)}/><label className="field-wrap"><span className="field-label"><TexteLocalise phrase="Fournisseur"/></span><select className="field-control" value={formulaire.fournisseur} onChange={(e) => setFormulaire({ ...formulaire, fournisseur: e.target.value })}><option value=""><TexteLocalise phrase="Sans fournisseur"/></option>{fournisseurs.map((f) => <option key={f.id} value={f.id}>{f.nom}</option>)}</select></label></div>
          <Input label="Référence du reçu (facultative)" maxLength={100} value={formulaire.reference} onChange={(e) => setFormulaire({ ...formulaire, reference: e.target.value })}/>
          <Input label="Note (facultative)" maxLength={250} value={formulaire.note} onChange={(e) => setFormulaire({ ...formulaire, note: e.target.value })}/>
        </div>
        <div className="space-y-3">{formulaire.lignes.map((ligne, index) => <div className="form-grid rounded-xl border border-line p-4" key={index}>
          <div className="space-y-2"><Input label="Rechercher un produit" value={rechercheProduit} onChange={(e) => setRechercheProduit(e.target.value)}/><label className="field-wrap"><span className="field-label"><TexteLocalise phrase="Produit"/></span><select className="field-control" required value={ligne.produit} onChange={(e) => changerLigne(index, "produit", e.target.value)}><option value=""><TexteLocalise phrase="Choisir un produit"/></option>{produits.map((p) => <option key={p.id} value={p.id}>{p.nom} · <TexteLocalise phrase="Stock"/> {p.quantite_stock}</option>)}</select></label></div>
          <Input label="Quantité reçue" type="number" min="1" step="1" required value={ligne.quantite} onChange={(e) => changerLigne(index, "quantite", e.target.value)}/>
          <Input label="Coût d’achat unitaire (FCFA)" type="number" min="0" step="0.01" required value={ligne.prix_achat_unitaire} onChange={(e) => changerLigne(index, "prix_achat_unitaire", e.target.value)}/>
          {formulaire.lignes.length > 1 && <div className="form-actions"><Button variant="danger" size="small" onClick={() => setFormulaire((ancien) => ({ ...ancien, lignes: ancien.lignes.filter((_, i) => i !== index) }))}><TexteLocalise phrase="Retirer"/></Button></div>}
        </div>)}</div>
        <div className="form-actions"><Button variant="secondary" onClick={() => setFormulaire((ancien) => ({ ...ancien, lignes: [...ancien.lignes, ligneVide()] }))}><Icon name="plus" size={17}/><TexteLocalise phrase="Ajouter un produit à la réception"/></Button><Button type="submit" disabled={envoi || !produits.length}>{envoi ? <TexteLocalise phrase="Enregistrement…"/> : <><Icon name="box" size={17}/><TexteLocalise phrase="Confirmer la réception et le stock"/></>}</Button></div>
      </form>
      {!produits.length && !chargement && <p className="mt-3 text-sm text-ink-muted"><TexteLocalise phrase="Ajoutez d’abord des produits à votre catalogue."/> <Link className="font-semibold text-brand" to="/produits"><TexteLocalise phrase="Voir les produits"/></Link></p>}
    </Card>
    <div className="filter-row"><div><h2 className="m-0 text-lg font-semibold"><TexteLocalise phrase="Réceptions récentes"/></h2><p className="mt-1 text-sm text-ink-muted">{total} <TexteLocalise phrase="réception(s)"/></p></div></div>
    {chargement ? <div className="product-card-grid">{[1, 2, 3].map((n) => <SkeletonCard key={n}/>)}</div> : receptions.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="box" size={25}/></span><h3><TexteLocalise phrase="Aucune réception enregistrée"/></h3><p><TexteLocalise phrase="Les achats confirmés apparaîtront ici avec le détail des quantités reçues."/></p></Card> : <div className="space-y-3">{receptions.map((r) => <Card key={r.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{r.fournisseur_nom || traduire("Fournisseur non renseigné")}</h3><p className="text-sm text-ink-muted">{r.reference || `Réception #${r.id}`} · {new Date(r.date_reception).toLocaleString()}</p>{r.note && <p className="mt-1 text-sm">{r.note}</p>}</div><strong>{formaterFCFA(r.total)}</strong></div><div className="mt-4 divide-y divide-line">{(r.details || []).map((d) => <div key={d.id} className="flex flex-wrap justify-between gap-2 py-2 text-sm"><span>{d.produit_nom} · {d.quantite} × {formaterFCFA(d.prix_achat_unitaire)}</span><strong>{formaterFCFA(d.total)}</strong></div>)}</div></Card>)}</div>}
    <Pagination page={page} count={total} onChange={setPage}/>
  </>;
}
