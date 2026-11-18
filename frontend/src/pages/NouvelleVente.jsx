import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

export default function NouvelleVente() {
  const [produits,setProduits]=useState([]), [clients,setClients]=useState([]);
  const [produitId,setProduitId]=useState(""), [quantite,setQuantite]=useState(1), [clientId,setClientId]=useState("");
  const [rechercheProduit,setRechercheProduit]=useState(""), [rechercheClient,setRechercheClient]=useState("");
  const [chargement,setChargement]=useState(true), [enregistrement,setEnregistrement]=useState(false), [erreur,setErreur]=useState("");
  const notifier=useToast();
  useEffect(()=>{let actif=true;const delai=setTimeout(async()=>{try{const [p,c]=await Promise.all([api.get("/api/produits/",{params:{page_size:100,recherche:rechercheProduit||undefined}}),api.get("/api/clients/",{params:{page_size:100,recherche:rechercheClient||undefined}})]);if(actif){setProduits(extraireListe(p.data));setClients(extraireListe(c.data));}}catch(error){const texte=messageErreur(error);if(actif){setErreur(texte);notifier(texte,"error");}}finally{if(actif)setChargement(false);}},250);return()=>{actif=false;clearTimeout(delai);};},[rechercheProduit,rechercheClient,notifier]);
  const produit=produits.find((p)=>String(p.id)===produitId);
  const total=useMemo(()=>Number(produit?.prix||0)*Number(quantite||0),[produit,quantite]);
  async function selectionnerCodeBarres(code) {
    const valeur = code.trim();
    if (!valeur) return;
    try {
      const { data } = await api.get("/api/produits/", { params: { recherche: valeur, page_size: 100 } });
      const resultat = extraireListe(data);
      setProduits(resultat);
      const correspondance = resultat.find((item) => item.code_barres?.toLowerCase() === valeur.toLowerCase()) || (resultat.length === 1 ? resultat[0] : null);
      if (!correspondance) { setErreur(traduire("Aucun produit ne correspond à ce code-barres.")); return; }
      if (correspondance.quantite_stock < 1) { setErreur(traduire("Ce produit est en rupture de stock.")); return; }
      setProduitId(String(correspondance.id)); setErreur("");
    } catch (error) { setErreur(messageErreur(error)); }
  }
  async function enregistrer(event){event.preventDefault();setErreur("");setEnregistrement(true);const produitVendu=Number(produitId),quantiteVendue=Number(quantite);try{await api.post("/api/ventes/",{produit:produitVendu,client:clientId?Number(clientId):null,quantite:quantiteVendue});notifier("Vente enregistrée et stock mis à jour.");setProduits((anciens)=>anciens.map((item)=>item.id===produitVendu?{...item,quantite_stock:Math.max(0,item.quantite_stock-quantiteVendue)}:item));setProduitId("");setRechercheProduit("");setQuantite(1);setClientId("");}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}finally{setEnregistrement(false);}}
  if(chargement)return <><div className="page-heading"><div><h1>{<TexteLocalise phrase={"Nouvelle vente"} />}</h1><p>{<TexteLocalise phrase={"Enregistrez un achat en quelques instants."} />}</p></div></div><SkeletonCard/></>;
  const disponibles=produits.filter((p)=>p.quantite_stock>0);
  return <>
    <div className="page-heading"><div><span className="form-eyebrow">{<TexteLocalise phrase={"Encaissement"} />}</span><h1>{<TexteLocalise phrase={"Nouvelle vente"} />}</h1><p>{<TexteLocalise phrase={"Choisissez un produit et indiquez la quantité vendue."} />}</p></div><Link to="/ventes/historique" className="btn-ghost"><Icon name="clock" size={17}/>{<TexteLocalise phrase={"Historique"} />}</Link></div>
    {erreur&&<div className="alert-box mb-4" role="alert">{erreur}</div>}
    {disponibles.length===0?<Card className="empty-state"><span className="empty-icon"><Icon name="cart" size={25}/></span><h3>{<TexteLocalise phrase={"Aucun produit en stock"} />}</h3><p>{<TexteLocalise phrase={"Ajoutez un produit ou mettez à jour les quantités avant d’enregistrer une vente."} />}</p><Link to="/produits" className="btn-primary mt-2">{<TexteLocalise phrase={"Gérer les produits"} />}{' '}<Icon name="arrow" size={16}/></Link></Card>:
      <div className="sale-layout"><Card className="sale-form-card"><form onSubmit={enregistrer} className="sale-form">
        <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Rechercher un produit"} />}</span><input className="field-control" value={rechercheProduit} onChange={(e)=>{setRechercheProduit(e.target.value);setProduitId("");}} onKeyDown={(event)=>{if(event.key==="Enter"){event.preventDefault();selectionnerCodeBarres(rechercheProduit);}}} placeholder={traduire("Nom du produit ou code-barres")}/><span className="field-hint"><TexteLocalise phrase="Un lecteur de codes-barres USB ou Bluetooth peut être utilisé comme un clavier."/></span></label>
        <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Produit vendu"} />}</span><select className="field-control" required value={produitId} onChange={(e)=>setProduitId(e.target.value)}><option value="">{<TexteLocalise phrase={"Sélectionner dans les résultats"} />}</option>{disponibles.map((p)=><option key={p.id} value={p.id}>{p.nom} — {formaterFCFA(p.prix)}</option>)}</select></label>
        {produit&&<div className="sale-product-hint"><span className="product-icon"><Icon name="box" size={19}/></span><span><strong>{produit.nom}</strong><small>{produit.quantite_stock}{' '}{<TexteLocalise phrase={"unités disponibles"} />}</small></span><strong className="ml-auto">{formaterFCFA(produit.prix)}</strong></div>}
        <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Quantité"} />}</span><div className="quantity-control"><button type="button" className="quantity-button" aria-label={traduire("Diminuer")} onClick={()=>setQuantite((n)=>Math.max(1,Number(n)-1))}>−</button><input className="field-control quantity-input" type="number" min="1" max={produit?.quantite_stock||undefined} step="1" required value={quantite} onChange={(e)=>setQuantite(e.target.value)}/><button type="button" className="quantity-button" aria-label={traduire("Augmenter")} disabled={Boolean(produit)&&Number(quantite)>=produit.quantite_stock} onClick={()=>setQuantite((n)=>Number(n)+1)}>+</button></div>{produit&&Number(quantite)>produit.quantite_stock&&<small className="text-red-700">{<TexteLocalise phrase={"Quantité supérieure au stock disponible."} />}</small>}</label>
        <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Rechercher un client"} />}</span><input className="field-control" value={rechercheClient} onChange={(e)=>{setRechercheClient(e.target.value);setClientId("");}} placeholder={traduire("Nom ou téléphone (facultatif)")}/></label>
        <label className="field-wrap"><span className="field-label">{<TexteLocalise phrase={"Associer un client"} />}{' '}<small className="font-normal text-ink-muted">{<TexteLocalise phrase={"(facultatif)"} />}</small></span><select className="field-control" value={clientId} onChange={(e)=>setClientId(e.target.value)}><option value="">{<TexteLocalise phrase={"Vente sans client"} />}</option>{clients.map((c)=><option value={c.id} key={c.id}>{c.nom}</option>)}</select></label>
        <div className="sale-total"><span><small>{<TexteLocalise phrase={"Total de la vente"} />}</small><strong>{formaterFCFA(total)}</strong></span><span className="sale-total-icon"><Icon name="wallet" size={22}/></span></div>
        <Button type="submit" className="w-full" disabled={enregistrement||!produit||Number(quantite)>produit?.quantite_stock}>{enregistrement?"Enregistrement…":<><Icon name="check" size={17}/>{<TexteLocalise phrase={"Confirmer la vente"} />}</>}</Button>
      </form></Card><aside className="sale-side-note"><span className="empty-icon"><Icon name="shield" size={22}/></span><h2>{<TexteLocalise phrase={"Stock mis à jour automatiquement"} />}</h2><p>{<TexteLocalise phrase={"Le prix enregistré pour cette vente est celui du produit au moment de l’achat. Le stock diminue dès la confirmation."} />}</p></aside></div>}
  </>;
}
