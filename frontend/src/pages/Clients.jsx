import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import DicteeVocale from "../composants/DicteeVocale";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import { SkeletonCard } from "../composants/Skeleton";
import Pagination from "../composants/Pagination";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";
import { extraireChampsDictee } from "../utils/dicteeVocale";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

export default function Clients(){
  const [clients,setClients]=useState([]),[nom,setNom]=useState(""),[telephone,setTelephone]=useState("");
  const [chargement,setChargement]=useState(true),[ajout,setAjout]=useState(false),[erreur,setErreur]=useState(""),[page,setPage]=useState(1),[nombreClients,setNombreClients]=useState(0);
  const notifier=useToast();
  const charger=useCallback(async()=>{setChargement(true);try{const {data}=await api.get("/api/clients/",{params:{page}});setClients(extraireListe(data));setNombreClients(data.count??extraireListe(data).length);}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}finally{setChargement(false);}},[page,notifier]);
  useEffect(()=>{charger();},[charger]);
  function dicterClient(phrase){
    const champs=extraireChampsDictee(phrase,{
      nom:{aliases:["nom du client","client","nom","customer","name"]},
      telephone:{aliases:["telephone","numero de telephone","phone","tel"],type:"phone"},
    });
    if(champs.nom)setNom(champs.nom);
    if(champs.telephone)setTelephone(champs.telephone);
  }
  async function ajouter(event){event.preventDefault();setErreur("");setAjout(true);try{await api.post("/api/clients/",{nom:nom.trim(),telephone:telephone.trim()});setNom("");setTelephone("");notifier("Client ajouté.");await charger();}catch(error){const texte=messageErreur(error);setErreur(texte);notifier(texte,"error");}finally{setAjout(false);}}
  return <>
    <div className="page-heading"><div><span className="form-eyebrow">{<TexteLocalise phrase={"Carnet clients"} />}</span><h1>{<TexteLocalise phrase={"Clients"} />}</h1><p>{<TexteLocalise phrase={"Retrouvez les contacts et les soldes de vos clients."} />}</p></div><Badge tone="neutral">{nombreClients}{' '}{<TexteLocalise phrase={"client"} />}{nombreClients>1?"s":""}</Badge></div>
    {erreur&&<div className="alert-box mb-4" role="alert">{erreur}</div>}
    <Card className="mb-5"><div className="section-card-heading"><div><h2>{<TexteLocalise phrase={"Ajouter un client"} />}</h2><p>{<TexteLocalise phrase={"Le téléphone est facultatif."} />}</p></div><span className="feature-icon"><Icon name="users" size={21}/></span></div>
      <DicteeVocale onTranscription={dicterClient} aide="Dictez le nom du client et, si besoin, son numéro de téléphone. Exemple : Awa Soglo, téléphone +229 01 02 03 04 05."/>
      <form onSubmit={ajouter} className="form-grid"><Input label="Nom du client" placeholder={traduire("Ex. Awa S.")} required value={nom} onChange={(e)=>setNom(e.target.value)}/><Input label="Téléphone" type="tel" placeholder={traduire("Ex. +229 01 00 00 00 00")} value={telephone} onChange={(e)=>setTelephone(e.target.value)}/><div className="form-actions col-span-full"><Button type="submit" disabled={ajout}>{ajout?"Ajout…":<><Icon name="plus" size={17}/>{<TexteLocalise phrase={"Ajouter le client"} />}</>}</Button></div></form>
    </Card>
    <div className="section-card-heading"><div><h2>{<TexteLocalise phrase={"Votre clientèle"} />}</h2><p>{<TexteLocalise phrase={"Le solde reflète les dettes moins les paiements enregistrés."} />}</p></div></div>
    {chargement?<div className="client-card-grid">{[1,2,3,4].map((n)=><SkeletonCard key={n}/>)}</div>:clients.length===0?<Card className="empty-state"><span className="empty-icon"><Icon name="users" size={25}/></span><h3>{<TexteLocalise phrase={"Aucun client pour le moment"} />}</h3><p>{<TexteLocalise phrase={"Ajoutez votre premier client pour suivre ses achats à crédit et ses remboursements."} />}</p></Card>:
      <div className="client-card-grid">{clients.map((client)=><Link to={`/clients/${client.id}`} key={client.id} className="client-card-link"><Card className="client-card"><div className="client-avatar">{client.nom?.trim()?.charAt(0)?.toUpperCase()||"C"}</div><div className="client-card-main"><h3>{client.nom}</h3><p>{client.telephone||"Aucun téléphone indiqué"}</p></div><Icon name="arrow" className="client-arrow" size={17}/><div className="client-balance"><span>{<TexteLocalise phrase={"Solde en cours"} />}</span><strong>{formaterFCFA(client.solde)}</strong></div><Badge tone={Number(client.solde)>0?"amber":"green"}>{Number(client.solde)>0?"À régler":"À jour"}</Badge></Card></Link>)}</div>}
    <Pagination page={page} count={nombreClients} onChange={setPage}/>
  </>;
}
