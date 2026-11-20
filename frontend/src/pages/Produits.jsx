import { useCallback, useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Badge from "../composants/Badge";
import Button from "../composants/Button";
import Card from "../composants/Card";
import DicteeVocale from "../composants/DicteeVocale";
import ScannerCodeProduit from "../composants/ScannerCodeProduit";
import Icon from "../composants/Icon";
import Input from "../composants/Input";
import Modal from "../composants/Modal";
import { SkeletonCard } from "../composants/Skeleton";
import Pagination from "../composants/Pagination";
import { useToast } from "../composants/ToastProvider";
import { extraireListe, formaterFCFA } from "../utils";
import { TexteLocalise, traduire } from "../contexte/LangueContext";
import { Link } from "react-router-dom";

const vide = { nom: "", code_barres: "", prix: "", prix_achat: "", quantite_stock: 0, seuil_alerte: 5, date_peremption: "" };

const CHAMPS_VOCAUX = [
  { cle: "code_barres", libelles: ["code-barres", "code barre", "barcode", "codigo de barras", "código de barras", "الباركود"] },
  { cle: "date_peremption", libelles: ["date de peremption", "date d'expiration", "date expiration", "date limite", "peremption", "expiration", "expiry date", "best before", "use by", "fecha de caducidad", "fecha de vencimiento", "data de validade", "تاريخ الصلاحية"] },
  { cle: "prix_achat", libelles: ["prix d'achat", "prix achat", "cout d'achat", "achat", "purchase price", "cost price", "precio de compra", "preco de compra", "سعر الشراء"] },
  { cle: "seuil_alerte", libelles: ["seuil d'alerte", "seuil", "threshold", "umbral", "limite", "حد التنبيه"] },
  { cle: "quantite_stock", libelles: ["quantite en stock", "quantite", "stock", "quantity", "cantidad", "quantidade", "الكمية", "المخزون"] },
  { cle: "prix", libelles: ["prix de vente", "prix vente", "vente", "selling price", "sale price", "precio de venta", "preco de venda", "سعر البيع"] },
];

function normaliserTexteVocal(texte) {
  return texte.toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[’`]/g, "'")
    .replace(/[٠-٩]/g, (chiffre) => String("٠١٢٣٤٥٦٧٨٩".indexOf(chiffre)))
    .replace(/[۰-۹]/g, (chiffre) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(chiffre)));
}

function nombreDepuisTexte(texte) {
  const chiffres = normaliserTexteVocal(texte).match(/\d[\d\s.,]*/);
  if (chiffres) {
    let valeur = chiffres[0].replace(/\s/g, "").replace(/[^\d.,]/g, "");
    const derniereVirgule = valeur.lastIndexOf(",");
    const dernierPoint = valeur.lastIndexOf(".");
    const separateurDecimal = Math.max(derniereVirgule, dernierPoint);
    if (separateurDecimal >= 0 && valeur.length - separateurDecimal - 1 === 3 && !(derniereVirgule >= 0 && dernierPoint >= 0)) {
      valeur = valeur.replace(/[.,]/g, "");
    } else if (derniereVirgule >= 0 && dernierPoint >= 0) {
      const separateurMilliers = separateurDecimal === derniereVirgule ? /\./g : /,/g;
      valeur = valeur.replace(separateurMilliers, "").replace(separateurDecimal === derniereVirgule ? "," : ".", ".");
    } else {
      valeur = valeur.replace(",", ".");
    }
    const nombre = Number(valeur);
    if (Number.isFinite(nombre)) return String(nombre);
  }

  const mots = normaliserTexteVocal(texte).match(/[a-z]+/g) || [];
  const unites = { zero: 0, un: 1, une: 1, deux: 2, trois: 3, quatre: 4, cinq: 5, six: 6, sept: 7, huit: 8, neuf: 9, dix: 10, onze: 11, douze: 12, treize: 13, quatorze: 14, quinze: 15, seize: 16 };
  const dizaines = { vingt: 20, trente: 30, quarante: 40, cinquante: 50, soixante: 60, septante: 70, octante: 80, nonante: 90, quatrevingt: 80 };
  let total = 0;
  let courant = 0;
  let reconnu = false;
  for (let index = 0; index < mots.length; index += 1) {
    const mot = mots[index].replace(/-/g, "");
    if (mot === "et" || mot === "a" || mot === "cfa" || mot === "fcfa" || mot === "franc" || mot === "francs") continue;
    if (mot === "quatre" && ["vingt", "vingts"].includes(mots[index + 1])) {
      courant += 80; reconnu = true; index += 1;
      if (["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"].includes(mots[index + 1])) courant += unites[mots[++index]];
      else if (unites[mots[index + 1]] !== undefined) courant += unites[mots[++index]];
      continue;
    }
    if (dizaines[mot]) {
      courant += dizaines[mot]; reconnu = true;
    } else if (unites[mot] !== undefined) {
      courant += unites[mot]; reconnu = true;
    } else if (mot === "cent" || mot === "cents") {
      courant = (courant || 1) * 100; reconnu = true;
    } else if (mot === "mille") {
      total += (courant || 1) * 1000; courant = 0; reconnu = true;
    }
  }
  return reconnu ? String(total + courant) : "";
}

function dateDepuisTexte(texte) {
  const normalise = normaliserTexteVocal(texte).replace(/,/g, " ").trim();
  const valider = (annee, mois, jour) => {
    const date = new Date(Number(annee), Number(mois) - 1, Number(jour));
    return date.getFullYear() === Number(annee) && date.getMonth() === Number(mois) - 1 && date.getDate() === Number(jour)
      ? `${annee}-${String(mois).padStart(2, "0")}-${String(jour).padStart(2, "0")}` : "";
  };
  const iso = normalise.match(/\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b/);
  if (iso) return valider(iso[1], iso[2], iso[3]);
  const numeric = normalise.match(/\b(\d{1,2})[/. -](\d{1,2})[/. -](20\d{2})\b/);
  if (numeric) return valider(numeric[3], numeric[2], numeric[1]);
  const mois = { janvier: "01", jan: "01", january: "01", febrero: "02", fevrier: "02", feb: "02", february: "02", mars: "03", marzo: "03", march: "03", avril: "04", abril: "04", april: "04", maio: "05", mai: "05", mayo: "05", may: "05", juin: "06", junio: "06", june: "06", juillet: "07", julio: "07", july: "07", aout: "08", agosto: "08", august: "08", septembre: "09", setiembre: "09", septiembre: "09", september: "09", octobre: "10", octubre: "10", october: "10", novembre: "11", noviembre: "11", november: "11", decembre: "12", diciembre: "12", dezembro: "12", december: "12" };
  const textuel = normalise.match(/\b(\d{1,2})\s+([a-z]+)\s+(20\d{2})\b/);
  if (!textuel || !mois[textuel[2]]) return "";
  return valider(textuel[3], mois[textuel[2]], textuel[1]);
}

function analyserDicteeProduit(texte) {
  const normalise = normaliserTexteVocal(texte);
  const reperes = [];
  for (const champ of CHAMPS_VOCAUX) {
    for (const libelle of champ.libelles) {
      const libelleNormalise = normaliserTexteVocal(libelle);
      const expression = new RegExp(`(^|[^\\p{L}\\p{N}])(${libelleNormalise.replace(/ /g, "\\s+")})(?=$|[^\\p{L}\\p{N}])`, "giu");
      for (const correspondance of normalise.matchAll(expression)) {
        const debut = correspondance.index + correspondance[1].length;
        reperes.push({ cle: champ.cle, debut, fin: debut + correspondance[2].length });
      }
    }
  }
  reperes.sort((a, b) => a.debut - b.debut || b.fin - a.fin);
  const uniques = reperes.filter((repere, index) => !reperes.slice(0, index).some((precedent) => precedent.cle === repere.cle && repere.debut < precedent.fin));
  const resultats = {};
  if (uniques.length) {
    const nom = texte.slice(0, indexOriginalDepuisNormalise(texte, uniques[0].debut)).replace(/^\s*(ajoute|ajouter|cr[eé]e|cr[eé]er)?\s*(un\s+)?(produit\s+)?/i, "").replace(/[\s,;:.]+$/, "").trim();
    if (nom) resultats.nom = nom;
    uniques.forEach((repere, index) => {
      const fin = uniques[index + 1]?.debut ?? texte.length;
      const segment = texte.slice(repere.fin, fin);
      const valeur = repere.cle === "date_peremption"
        ? dateDepuisTexte(segment)
        : repere.cle === "code_barres"
        ? (normaliserTexteVocal(segment).match(/[\d\s]+/)?.[0].replace(/\D/g, "") || "")
        : nombreDepuisTexte(segment);
      if (valeur !== "") resultats[repere.cle] = valeur;
    });
  } else {
    const nom = texte.replace(/^\s*(ajoute|ajouter|cr[eé]e|cr[eé]er)?\s*(un\s+)?(produit\s+)?/i, "").trim();
    if (nom) resultats.nom = nom;
  }
  return resultats;
}

function indexOriginalDepuisNormalise(texte, indexNormalise) {
  let offsetNormalise = 0;
  let offsetOriginal = 0;
  for (const caractere of texte) {
    if (offsetNormalise >= indexNormalise) break;
    offsetNormalise += normaliserTexteVocal(caractere).length;
    offsetOriginal += caractere.length;
  }
  return offsetOriginal;
}

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
  function editer(p) { setEditionId(p.id); setFormulaire({nom:p.nom,code_barres:p.code_barres || "",prix:p.prix,prix_achat:p.prix_achat ?? "",quantite_stock:p.quantite_stock,seuil_alerte:p.seuil_alerte,date_peremption:p.date_peremption || ""}); window.scrollTo({top:0,behavior:"smooth"}); }

  function dicterProduit(phrase) {
    const champs = analyserDicteeProduit(phrase);
    if (Object.keys(champs).length) setFormulaire((precedent) => ({ ...precedent, ...champs }));
  }

  async function enregistrer(event) {
    event.preventDefault(); setErreur(""); setEnregistrement(true);
    const corps = {...formulaire,prix:Number(formulaire.prix),prix_achat:formulaire.prix_achat === "" ? null : Number(formulaire.prix_achat),quantite_stock:Number(formulaire.quantite_stock),seuil_alerte:Number(formulaire.seuil_alerte),date_peremption:formulaire.date_peremption || null};
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

  async function appliquerCodeScanne(code) {
    changer("code_barres", code);
    try {
      const { data } = await api.get("/api/produits/", { params: { recherche: code, page_size: 100 } });
      const existant = extraireListe(data).find((produit) => produit.code_barres?.toLocaleLowerCase() === code.toLocaleLowerCase());
      if (!existant) return;
      setEditionId(existant.id);
      setFormulaire({
        nom: existant.nom, code_barres: existant.code_barres, prix: existant.prix,
        prix_achat: existant.prix_achat ?? "", quantite_stock: existant.quantite_stock,
        seuil_alerte: existant.seuil_alerte, date_peremption: existant.date_peremption || "",
      });
      notifier("Produit reconnu : ses informations ont été chargées.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch { /* Le code scanné reste saisi même si la recherche réseau échoue. */ }
  }

  function formaterDate(date) {
    if (!date) return "";
    const [annee, mois, jour] = date.split("-").map(Number);
    return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "long", year: "numeric" }).format(new Date(annee, mois - 1, jour));
  }

  return <>
    <div className="page-heading"><div><h1>{<TexteLocalise phrase={"Produits"} />}</h1><p>{<TexteLocalise phrase={"Gérez les prix et les quantités de votre stock."} />}</p></div><div className="flex flex-wrap items-center gap-2"><Link className="btn-secondary" to="/fournisseurs"><TexteLocalise phrase="Fournisseurs"/></Link><Link className="btn-secondary" to="/approvisionnements"><TexteLocalise phrase="Réceptionner du stock"/></Link><Badge tone="neutral">{nombreProduits}{' '}{<TexteLocalise phrase={"article"} />}{nombreProduits > 1 ? "s" : ""}</Badge></div></div>
    {erreur && <div className="alert-box mb-4" role="alert">{erreur}</div>}
    <Card className="mb-5"><div className="section-card-heading"><div><h2>{editionId ? <TexteLocalise phrase={"Modifier un produit"}/> : <TexteLocalise phrase={"Ajouter un produit"}/>}</h2><p>{<TexteLocalise phrase={"Saisissez le coût d’achat pour suivre automatiquement la marge brute sur les prochaines ventes."} />}</p></div>{editionId && <Button variant="ghost" onClick={reinitialiser}>{<TexteLocalise phrase={"Annuler"} />}</Button>}</div>
      {!editionId && <DicteeVocale onTranscription={dicterProduit} aide="Dictez le nom, le code-barres si besoin, les prix, la quantité, le seuil et la date de péremption. Exemple : Riz local, prix de vente 1 200, prix d’achat 800, quantité en stock 20, seuil d’alerte 5, date de péremption 30 juin 2027."/>}
      <form onSubmit={enregistrer} className="form-grid">
        <Input label="Nom du produit" required placeholder={traduire("Ex. Riz local")} value={formulaire.nom} onChange={(e)=>changer("nom",e.target.value)}/>
        <div className="barcode-field"><Input label="Code-barres ou QR (facultatif)" maxLength={64} placeholder={traduire("Scanner ou saisir le code")} value={formulaire.code_barres} onChange={(e)=>changer("code_barres",e.target.value)}/><ScannerCodeProduit onDetecte={appliquerCodeScanne}/></div>
        <Input label="Date de péremption (facultative)" type="date" value={formulaire.date_peremption} onChange={(e)=>changer("date_peremption",e.target.value)}/>
        <Input label="Prix de vente (FCFA)" type="number" min="0" step="1" required placeholder={traduire("0")} value={formulaire.prix} onChange={(e)=>changer("prix",e.target.value)}/>
        <Input label="Prix d’achat unitaire (FCFA)" type="number" min="0" step="0.01" required={!editionId} placeholder={traduire("Ex. 5 000")} value={formulaire.prix_achat} onChange={(e)=>changer("prix_achat",e.target.value)}/>
        <Input label="Quantité en stock" type="number" min="0" step="1" required value={formulaire.quantite_stock} onChange={(e)=>changer("quantite_stock",e.target.value)}/>
        <Input label="Seuil d’alerte" type="number" min="0" step="1" required value={formulaire.seuil_alerte} onChange={(e)=>changer("seuil_alerte",e.target.value)}/>
        <div className="form-actions col-span-full"><Button type="submit" disabled={enregistrement}>{enregistrement ? "Enregistrement…" : editionId ? "Enregistrer les changements" : <><Icon name="plus" size={17}/>{<TexteLocalise phrase={"Ajouter le produit"} />}</>}</Button></div>
      </form>
    </Card>

    <div className="filter-row"><div><h2 className="m-0 text-lg font-semibold">{<TexteLocalise phrase={"Votre catalogue"} />}</h2><p className="mt-1 text-sm text-ink-muted">{<TexteLocalise phrase={"Produits et niveaux de stock"} />}</p></div><label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={rupture} onChange={(e)=>{setRupture(e.target.checked);setPage(1);}} className="h-4 w-4 accent-brand"/>{<TexteLocalise phrase={"Sous le seuil"} />}</label></div>
    {chargement ? <div className="product-card-grid">{[1,2,3,4].map(n=><SkeletonCard key={n}/>)}</div> : produits.length === 0 ? <Card className="empty-state"><span className="empty-icon"><Icon name="box" size={26}/></span><h3>{rupture ? "Aucun stock à signaler" : "Aucun produit pour le moment"}</h3><p>{rupture ? "Tous vos produits sont au-dessus du seuil d’alerte." : "Ajoutez votre premier produit pour commencer à suivre votre stock."}</p></Card> :
      <div className="product-card-grid">{produits.map((p)=>{
        const margeUnitaire = p.prix_achat == null ? null : Number(p.prix) - Number(p.prix_achat);
        const valeurStock = Number(p.prix) * Number(p.quantite_stock);
        const margeStock = margeUnitaire == null ? null : margeUnitaire * Number(p.quantite_stock);
        return <Card key={p.id} className="product-item-card"><div className="product-item-top"><span className="product-icon"><Icon name="box" size={21}/></span><Badge tone={p.quantite_stock === 0 ? "red" : p.quantite_stock <= p.seuil_alerte ? "amber" : "green"}>{p.quantite_stock === 0 ? "Épuisé" : p.quantite_stock <= p.seuil_alerte ? "À renouveler" : "En stock"}</Badge></div><h3>{p.nom}</h3><p className="product-price">{formaterFCFA(p.prix)}</p><div className="product-stockline"><span>{<TexteLocalise phrase={"Coût d’achat unitaire"} />}</span><strong>{p.prix_achat == null ? <TexteLocalise phrase={"À renseigner"}/> : formaterFCFA(p.prix_achat)}</strong></div>{p.date_peremption && <div className="product-stockline"><span><TexteLocalise phrase="Date de péremption"/></span><strong>{formaterDate(p.date_peremption)}</strong></div>}<div className="product-stockline"><span>{<TexteLocalise phrase={"Marge brute unitaire"} />}</span><strong className={margeUnitaire != null && margeUnitaire < 0 ? "text-red-700" : ""}>{margeUnitaire == null ? "—" : formaterFCFA(margeUnitaire)}</strong></div><div className="product-stockline"><span>{<TexteLocalise phrase={"Valeur de vente du stock"} />}</span><strong>{formaterFCFA(valeurStock)}</strong></div><div className="product-stockline"><span>{<TexteLocalise phrase={"Marge potentielle du stock"} />}</span><strong className={margeStock != null && margeStock < 0 ? "text-red-700" : ""}>{margeStock == null ? "—" : formaterFCFA(margeStock)}</strong></div><div className="product-stockline"><span>{<TexteLocalise phrase={"Quantité"} />}</span><strong>{p.quantite_stock} <small>{<TexteLocalise phrase={"unités"} />}</small></strong></div><div className="product-stockline"><span>{<TexteLocalise phrase={"Seuil d’alerte"} />}</span><span>{p.seuil_alerte}</span></div><div className="product-actions"><Button variant="secondary" size="small" onClick={()=>editer(p)}>{<TexteLocalise phrase={"Modifier"} />}</Button><Button variant="danger" size="small" onClick={()=>setProduitASupprimer(p)}>{<TexteLocalise phrase={"Archiver"} />}</Button></div></Card>})}</div>}
    <Pagination page={page} count={nombreProduits} onChange={setPage}/>
    <Modal open={Boolean(produitASupprimer)} title={traduire("Archiver ce produit ?")} onClose={()=>setProduitASupprimer(null)}>{produitASupprimer && <><p className="mb-5 text-sm leading-6 text-ink-muted">{<TexteLocalise phrase={"Le produit"} />}{' '}<strong>{produitASupprimer.nom}</strong>{' '}{<TexteLocalise phrase={"sera masqué du catalogue. Son stock et ses ventes passées restent conservés."} />}</p><div className="form-actions justify-end"><Button variant="secondary" onClick={()=>setProduitASupprimer(null)}>{<TexteLocalise phrase={"Annuler"} />}</Button><Button variant="danger" onClick={supprimer}>{<TexteLocalise phrase={"Archiver"} />}</Button></div></>}</Modal>
  </>;
}
