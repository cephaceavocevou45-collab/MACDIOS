import { useCallback, useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Modal from "../composants/Modal";
import { SkeletonCard } from "../composants/Skeleton";
import Pagination from "../composants/Pagination";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";

const vide = { nom: "", prix: "", quantite_stock: 0, seuil_alerte: 5 };

export default function Produits() {
  const [produits, setProduits] = useState([]);
  const [formulaire, setFormulaire] = useState(vide);
  const [editionId, setEditionId] = useState(null);
  const [produitASupprimer, setProduitASupprimer] = useState(null);
  const [rupture, setRupture] = useState(false);
  const [page, setPage] = useState(1);
  const [nombreProduits, setNombreProduits] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();

  const charger = useCallback(async () => {
    setChargement(true); setErreur("");
    try { const { data } = await api.get("/api/produits/", { params: { page, ...(rupture ? {rupture:"true"} : {}) } }); setProduits(extraireListe(data)); setNombreProduits(data.count ?? extraireListe(data).length); }
    catch (error) { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); }
    finally { setChargement(false); }
  }, [page, rupture, notifier]);
  useEffect(() => { charger(); }, [charger]);
  function changer(cle,valeur) { setFormulaire((ancien) => ({...ancien,[cle]:valeur})); }
  function reinitialiser() { setEditionId(null); setFormulaire(vide); }
  function editer(p) { setEditionId(p.id); setFormulaire({nom:p.nom,prix:p.prix,quantite_stock:p.quantite_stock,seuil_alerte:p.seuil_alerte}); window.scrollTo({top:0,behavior:"smooth"}); }

  async function enregistrer(event) {
    event.preventDefault(); setErreur(""); setEnregistrement(true);
    const corps = {...formulaire,prix:Number(formulaire.prix),quantite_stock:Number(formulaire.quantite_stock),seuil_alerte:Number(formulaire.seuil_alerte)};
    try {
      if (editionId) { await api.put(`/api/produits/${editionId}/`, corps); notifier("Produit modifié."); }
      else { await api.post("/api/produits/", corps); notifier("Produit ajouté."); }
      reinitialiser(); await charger();
    } catch (error) { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); }
    finally { setEnregistrement(false); }
  }

  async function supprimer() {
    try { await api.delete(`/api/produits/${produitASupprimer.id}/`); notifier("Produit archivé. Les ventes passées sont conservées."); setProduitASupprimer(null); await charger(); }
    catch (error) { const texte = messageErreur(error); setErreur(texte); notifier(texte, "error"); setProduitASupprimer(null); }
  }

  return <>
    <div className="page-heading"><div><h1>Produits</h1><p>Gérez les prix et les quantités de votre stock.</p></div><Badge tone="neutral">{nombreProduits} article{nombreProduits > 1 ? "s" : ""}</Badge></div>
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <Card className="mb-5"><div className="section-card-heading"><div><h2>{editionId ? "Modifier un produit" : "Ajouter un produit"}</h2><p>Les quantités et les prix peuvent être ajustés à tout moment.</p></div>{editionId && <Button variant="ghost" onClick={reinitialiser}>Annuler</Button>}</div>
      <form onSubmit={enregistrer} className="form-grid">
        <Input label="Nom du produit" required placeholder="Ex. Riz local" value={formulaire.nom} onChange={(e)=>changer("nom",e.target.value)}/>
        <Input label="Prix de vente (FCFA)" type="number" min="0" step="1" required placeholder="0" value={formulaire.prix} onChange={(e)=>changer("prix",e.target.value)}/>
        <Input label="Quantité en stock" type="number" min="0" step="1" required value={formulaire.quantite_stock} onChange={(e)=>changer("quantite_stock",e.target.value)}/>
        <Input label="Seuil d’alerte" type="number" min="0" step="1" required value={formulaire.seuil_alerte} onChange={(e)=>changer("seuil_alerte",e.target.value)}/>
        <div className="form-actions col-span-full"><Button type="submit" disabled={enregistrement}>{enregistrement ? "Enregistrement…" : editionId ? "Enregistrer les changements" : <><Icon name="plus" size={17}/>Ajouter le produit</>}</Button></div>
      </form>
    </Card>

    <div className="filter-row"><div><h2 className="m-0 text-lg font-semibold">Votre catalogue</h2><p className="mt-1 text-sm text-ink-muted">Produits et niveaux de stock</p></div><label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={rupture} onChange={(e)=>{setRupture(e.target.checked);setPage(1);}} className="h-4 w-4 accent-brand"/>Sous le seuil</label></div>
    {chargement ? <div className="product-card-grid">{[1,2,3,4].map(n=><SkeletonCard key={n}/>)}</div> : produits.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="box" size={26}/></span><h3>{rupture ? "Aucun stock à signaler" : "Aucun produit pour le moment"}</h3><p>{rupture ? "Tous vos produits sont au-dessus du seuil d’alerte." : "Ajoutez votre premier produit pour commencer à suivre votre stock."}</p></Card> :
      <div className="product-card-grid">{produits.map((p)=><Card key={p.id} className="product-item-card"><div className="product-item-top"><span className="product-icon"><Icon name="box" size={21}/></span><Badge tone={p.quantite_stock === 0 ? "red" : p.quantite_stock <= p.seuil_alerte ? "amber" : "green"}>{p.quantite_stock === 0 ? "Épuisé" : p.quantite_stock <= p.seuil_alerte ? "À renouveler" : "En stock"}</Badge></div><h3>{p.nom}</h3><p className="product-price">{formaterFCFA(p.prix)}</p><div className="product-stockline"><span>Quantité</span><strong>{p.quantite_stock} <small>unités</small></strong></div><div className="product-stockline"><span>Seuil d’alerte</span><span>{p.seuil_alerte}</span></div><div className="product-actions"><Button variant="secondary" size="small" onClick={()=>editer(p)}>Modifier</Button><Button variant="danger" size="small" onClick={()=>setProduitASupprimer(p)}>Archiver</Button></div></Card>)}</div>}
    <Pagination page={page} count={nombreProduits} onChange={setPage}/>
    <Modal open={Boolean(produitASupprimer)} title="Archiver ce produit ?" onClose={()=>setProduitASupprimer(null)}>{produitASupprimer && <><p className="mb-5 text-sm leading-6 text-ink-muted">Le produit <strong>{produitASupprimer.nom}</strong> sera masqué du catalogue. Son stock et ses ventes passées restent conservés.</p><div className="form-actions justify-end"><Button variant="secondary" onClick={()=>setProduitASupprimer(null)}>Annuler</Button><Button variant="danger" onClick={supprimer}>Archiver</Button></div></>}</Modal>
  </>;
}
