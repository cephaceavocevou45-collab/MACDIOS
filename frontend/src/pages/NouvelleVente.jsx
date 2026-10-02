import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";

export default function NouvelleVente() {
  const [produits,setProduits]=useState([]), [clients,setClients]=useState([]);
  const [produitId,setProduitId]=useState(""), [quantite,setQuantite]=useState(1), [clientId,setClientId]=useState("");
  const [rechercheProduit,setRechercheProduit]=useState(""), [rechercheClient,setRechercheClient]=useState("");
  const [chargement,setChargement]=useState(true), [enregistrement,setEnregistrement]=useState(false), [erreur,setErreur]=useState("");
  const notifier=useToast();
  useEffect(()=>{let actif=true;const delai=setTimeout(async()=>{try{const [p,c]=await Promise.all([api.get("/api/produits/",{params:{page_size:100,recherche:rechercheProduit||undefined}}),api.get("/api/clients/",{params:{page_size:100,recherche:rechercheClient||undefined}})]);if(actif){setProduits(extraireListe(p.data));setClients(extraireListe(c.data));}}catch(error){const texte=messageErreur(error);if(actif){setErreur(texte);notifier(texte,"error");}}finally{if(actif)setChargement(false);}},250);return()=>{actif=false;clearTimeout(delai);};},[rechercheProduit,rechercheClient,notifier]);
  const produit=produits.find((p)=>String(p.id)===produitId);
  const total=useMemo(()=>Number(produit?.prix||0)*Number(quantite||0),[produit,quantite]);
  async function enregistrer(event){event.preventDefault();setErreur("");setEnregistrement(true);try{await api.post("/api/ventes/",{produit:Number(produitId),client:clientId?Number(clientId):null,quantite:Number(quantite)});notifier("Vente enregistrée et stock mis à jour.");setProduitId("");setQuantite(1);setClientId("");}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}finally{setEnregistrement(false);}}
  if(chargement)return <><div className="page-heading"><div><h1>Nouvelle vente</h1><p>Enregistrez un achat en quelques instants.</p></div></div><SkeletonCard/></>;
  const disponibles=produits.filter((p)=>p.quantite_stock>0);
  return <>
    <div className="page-heading"><div><span className="form-eyebrow">Encaissement</span><h1>Nouvelle vente</h1><p>Choisissez un produit et indiquez la quantité vendue.</p></div><Link to="/ventes/historique" className="btn-ghost"><Icon name="clock" size={17}/>Historique</Link></div>
    {erreur&&<div className="alert-box mb-4" role="alert">{erreur}</div>}
    {disponibles.length===0?<Card className="empty-state"><span className="empty-icon"><Icon name="cart" size={25}/></span><h3>Aucun produit en stock</h3><p>Ajoutez un produit ou mettez à jour les quantités avant d’enregistrer une vente.</p><Link to="/produits" className="btn-primary mt-2">Gérer les produits <Icon name="arrow" size={16}/></Link></Card>:
      <div className="sale-layout"><Card className="sale-form-card"><form onSubmit={enregistrer} className="sale-form">
        <label className="field-wrap"><span className="field-label">Rechercher un produit</span><input className="field-control" value={rechercheProduit} onChange={(e)=>{setRechercheProduit(e.target.value);setProduitId("");}} placeholder="Nom du produit"/></label>
        <label className="field-wrap"><span className="field-label">Produit vendu</span><select className="field-control" required value={produitId} onChange={(e)=>setProduitId(e.target.value)}><option value="">Sélectionner dans les résultats</option>{disponibles.map((p)=><option key={p.id} value={p.id}>{p.nom} — {formaterFCFA(p.prix)}</option>)}</select></label>
        {produit&&<div className="sale-product-hint"><span className="product-icon"><Icon name="box" size={19}/></span><span><strong>{produit.nom}</strong><small>{produit.quantite_stock} unités disponibles</small></span><strong className="ml-auto">{formaterFCFA(produit.prix)}</strong></div>}
        <label className="field-wrap"><span className="field-label">Quantité</span><div className="quantity-control"><button type="button" className="quantity-button" aria-label="Diminuer" onClick={()=>setQuantite((n)=>Math.max(1,Number(n)-1))}>−</button><input className="field-control quantity-input" type="number" min="1" max={produit?.quantite_stock||undefined} step="1" required value={quantite} onChange={(e)=>setQuantite(e.target.value)}/><button type="button" className="quantity-button" aria-label="Augmenter" disabled={Boolean(produit)&&Number(quantite)>=produit.quantite_stock} onClick={()=>setQuantite((n)=>Number(n)+1)}>+</button></div>{produit&&Number(quantite)>produit.quantite_stock&&<small className="text-red-700">Quantité supérieure au stock disponible.</small>}</label>
        <label className="field-wrap"><span className="field-label">Rechercher un client</span><input className="field-control" value={rechercheClient} onChange={(e)=>{setRechercheClient(e.target.value);setClientId("");}} placeholder="Nom ou téléphone (facultatif)"/></label>
        <label className="field-wrap"><span className="field-label">Associer un client <small className="font-normal text-ink-muted">(facultatif)</small></span><select className="field-control" value={clientId} onChange={(e)=>setClientId(e.target.value)}><option value="">Vente sans client</option>{clients.map((c)=><option value={c.id} key={c.id}>{c.nom}</option>)}</select></label>
        <div className="sale-total"><span><small>Total de la vente</small><strong>{formaterFCFA(total)}</strong></span><span className="sale-total-icon"><Icon name="wallet" size={22}/></span></div>
        <Button type="submit" className="w-full" disabled={enregistrement||!produit||Number(quantite)>produit?.quantite_stock}>{enregistrement?"Enregistrement…":<><Icon name="check" size={17}/>Confirmer la vente</>}</Button>
      </form></Card><aside className="sale-side-note"><span className="empty-icon"><Icon name="shield" size={22}/></span><h2>Stock mis à jour automatiquement</h2><p>Le prix enregistré pour cette vente est celui du produit au moment de l’achat. Le stock diminue dès la confirmation.</p></aside></div>}
  </>;
}
