import { useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Card from "../composants/Card";
import Icon from "../composants/Icon";
import { SkeletonCard } from "../composants/Skeleton";
import { useToast } from "../composants/ToastProvider";
import { afficherDate, extraireListe, formaterFCFA } from "../utils";

export default function HistoriqueVentes(){
  const [periode,setPeriode]=useState("jour"),[ventes,setVentes]=useState([]),[produits,setProduits]=useState([]),[clients,setClients]=useState([]),[chargement,setChargement]=useState(true),[erreur,setErreur]=useState("");
  const notifier=useToast();
  // Les catalogues sont chargés une seule fois ; changer de période ne recharge que les ventes.
  useEffect(()=>{(async()=>{try{const [p,c]=await Promise.all([api.get("/api/produits/"),api.get("/api/clients/")]);setProduits(extraireListe(p.data));setClients(extraireListe(c.data));}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}})();},[notifier]);
  useEffect(()=>{(async()=>{setChargement(true);setErreur("");try{const {data}=await api.get("/api/ventes/",{params:{periode}});setVentes(extraireListe(data));}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}finally{setChargement(false);}})();},[periode,notifier]);
  const produitsParId=new Map(produits.map((p)=>[String(p.id),p.nom])),clientsParId=new Map(clients.map((c)=>[String(c.id),c.nom]));
  const total=ventes.reduce((s,v)=>s+Number(v.total||0),0);
  return <>
    <div className="page-heading"><div><span className="form-eyebrow">Vos encaissements</span><h1>Historique des ventes</h1><p>Retrouvez les ventes de la période choisie.</p></div><Badge tone="green">{ventes.length} vente{ventes.length>1?"s":""}</Badge></div>
    {erreur&&<div className="alert-box mb-4" role="alert">{erreur}</div>}
    <div className="history-summary"><div className="history-filter"><label className="field-wrap"><span className="field-label">Période</span><select className="field-control" value={periode} onChange={(e)=>setPeriode(e.target.value)}><option value="jour">Aujourd’hui</option><option value="semaine">Cette semaine</option><option value="mois">Ce mois</option></select></label></div><div><small>Total enregistré</small><strong>{formaterFCFA(total)}</strong></div></div>
    {chargement?<div className="grid gap-3">{[1,2,3].map((n)=><SkeletonCard key={n}/>)}</div>:ventes.length===0?<Card className="empty-state"><span className="empty-icon"><Icon name="chart" size={25}/></span><h3>Aucune vente sur cette période</h3><p>Vos ventes enregistrées apparaîtront ici. Vous pouvez en saisir une dès maintenant.</p></Card>:
      <div className="sales-list">{ventes.map((vente)=><Card key={vente.id} className="sale-history-card"><span className="sale-history-icon"><Icon name="cart" size={20}/></span><div className="sale-history-info"><strong>{produitsParId.get(String(vente.produit))||`Produit ${vente.produit}`}</strong><span>{vente.quantite} unité{vente.quantite>1?"s":""}{vente.client?` · ${clientsParId.get(String(vente.client))||`Client ${vente.client}`}`:" · Vente directe"}</span><small><Icon name="clock" size={13}/>{afficherDate(vente.date)}</small></div><strong className="sale-history-amount">{formaterFCFA(vente.total)}</strong></Card>)}</div>}
  </>;
}
