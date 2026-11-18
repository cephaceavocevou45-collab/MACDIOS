import { useEffect, useState } from "react";
import { api, messageErreur } from "../api";
import Button from "../composants/Button";
import Input from "../composants/Input";
import TelephoneInternational, { telephoneInternationalValide } from "../composants/TelephoneInternational";
import { useToast } from "../composants/ToastProvider";
import { useLangue, TexteLocalise, traduire } from "../contexte/LangueContext";

const PROFIL_VIDE = { nom_affiche: "", email: "", telephone: "", adresse: "", ville: "", logo_url: null };
const TYPES_IMAGE = ["image/jpeg", "image/png", "image/webp"];

export default function MonProfil() {
  const { langue } = useLangue();
  const [profil, setProfil] = useState(PROFIL_VIDE);
  const [fichier, setFichier] = useState(null);
  const [apercuLocal, setApercuLocal] = useState("");
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState("");
  const notifier = useToast();

  useEffect(() => {
    let actif = true;
    api.get("/api/profil/")
      .then(({ data }) => { if (actif) setProfil({ ...PROFIL_VIDE, ...data }); })
      .catch((e) => { if (actif) setErreur(messageErreur(e)); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, []);

  useEffect(() => {
    if (!fichier) { setApercuLocal(""); return undefined; }
    const url = URL.createObjectURL(fichier);
    setApercuLocal(url);
    return () => URL.revokeObjectURL(url);
  }, [fichier]);

  function choisirImage(event) {
    const image = event.target.files?.[0];
    event.target.value = "";
    if (!image) return;
    if (!TYPES_IMAGE.includes(image.type)) {
      setErreur("Choisissez une image JPEG, PNG ou WebP. Les fichiers SVG ne sont pas acceptés.");
      return;
    }
    if (image.size > 2 * 1024 * 1024) {
      setErreur("L'image ne doit pas dépasser 2 Mo.");
      return;
    }
    setErreur("");
    setFichier(image);
  }

  async function enregistrer(event) {
    event.preventDefault();
    setErreur("");
    setEnregistrement(true);
    const donnees = new FormData();
    donnees.append("nom_affiche", profil.nom_affiche.trim());
    donnees.append("telephone", profil.telephone.trim());
    donnees.append("adresse", profil.adresse.trim());
    donnees.append("ville", profil.ville.trim());
    if (fichier) donnees.append("logo", fichier);
    try {
      const { data } = await api.patch("/api/profil/", donnees, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setProfil({ ...PROFIL_VIDE, ...data });
      setFichier(null);
      window.dispatchEvent(new Event("profil-modifie"));
      notifier("Votre profil a été mis à jour.");
    } catch (e) {
      const texte = messageErreur(e);
      setErreur(texte);
      notifier(texte, "error");
    } finally { setEnregistrement(false); }
  }

  async function supprimerLogo() {
    if (!profil.logo_url && !fichier) return;
    if (!window.confirm("Supprimer le logo de votre profil ?")) return;
    setErreur("");
    if (fichier) { setFichier(null); return; }
    setEnregistrement(true);
    try {
      const { data } = await api.delete("/api/profil/photo/");
      setProfil({ ...PROFIL_VIDE, ...data });
      window.dispatchEvent(new Event("profil-modifie"));
      notifier("Le logo a été supprimé.");
    } catch (e) {
      const texte = messageErreur(e);
      setErreur(texte);
      notifier(texte, "error");
    } finally { setEnregistrement(false); }
  }

  if (chargement) return <section className="mx-auto max-w-3xl space-y-5" aria-label={traduire("Chargement du profil")}><div className="skeleton h-10 w-56"/><div className="skeleton h-80 rounded-2xl"/></section>;

  const image = apercuLocal || profil.logo_url;
  const initiales = profil.nom_affiche.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((mot) => mot[0].toUpperCase()).join("") || "N";

  return <section className="mx-auto max-w-3xl space-y-6">
    <header className="space-y-2">
      <span className="form-eyebrow">{<TexteLocalise phrase={"Compte"} />}</span>
      <h1 className="text-3xl font-bold text-ink">{<TexteLocalise phrase={"Mon profil"} />}</h1>
      <p className="text-ink-muted">{<TexteLocalise phrase={"Gérez le nom et les coordonnées affichés dans votre espace et sur vos documents PDF."} />}</p>
    </header>
    {erreur && <div className="alert-box" role="alert">{erreur}</div>}

    <form onSubmit={enregistrer} className="space-y-6 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-8">
      <div className="flex flex-col items-start gap-5 border-b border-line pb-6 sm:flex-row sm:items-center">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-brand/20 bg-brand/10 text-2xl font-bold text-brand">
          {image ? <img src={image} alt={traduire("Aperçu du logo de profil")} className="h-full w-full object-cover"/> : initiales}
        </div>
        <div className="space-y-3">
          <div><h2 className="font-semibold text-ink">{<TexteLocalise phrase={"Photo ou logo"} />}</h2><p className="text-sm text-ink-muted">{<TexteLocalise phrase={"JPEG, PNG ou WebP · 2 Mo maximum. L'image sera redimensionnée et nettoyée."} />}</p></div>
          <div className="flex flex-wrap gap-3">
            <label className="btn-secondary inline-flex cursor-pointer items-center justify-center">{<TexteLocalise phrase={"Choisir une image"} />}<input type="file" className="sr-only" accept="image/jpeg,image/png,image/webp" onChange={choisirImage}/>
            </label>
            {(profil.logo_url || fichier) && <Button type="button" variant="ghost" onClick={supprimerLogo} disabled={enregistrement}>{<TexteLocalise phrase={"Supprimer le logo"} />}</Button>}
          </div>
          {fichier && <p className="text-sm text-ink-muted">{<TexteLocalise phrase={"Nouvelle image :"} />}{' '}{fichier.name}</p>}
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Input label="Nom affiché" autoComplete="organization" maxLength={120} required value={profil.nom_affiche} onChange={(e) => setProfil({ ...profil, nom_affiche: e.target.value })}/>
        <Input label="Adresse email" type="email" value={profil.email} readOnly hint="L&apos;adresse email de connexion ne se modifie pas ici."/>
        <TelephoneInternational label="Téléphone de contact (facultatif)" value={profil.telephone} onChange={(telephone) => setProfil({ ...profil, telephone })} invalid={Boolean(profil.telephone) && !telephoneInternationalValide(profil.telephone)} hint="Visible sur les reçus. Choisissez le pays associé à votre numéro." langue={langue}/>
        <Input label="Ville" autoComplete="address-level2" maxLength={120} value={profil.ville} onChange={(e) => setProfil({ ...profil, ville: e.target.value })}/>
        <Input label="Adresse" autoComplete="street-address" maxLength={200} className="sm:col-span-2" value={profil.adresse} onChange={(e) => setProfil({ ...profil, adresse: e.target.value })}/>
      </div>
      <div className="flex justify-end border-t border-line pt-5">
        <Button type="submit" disabled={enregistrement}>{enregistrement ? "Enregistrement…" : "Enregistrer mon profil"}</Button>
      </div>
    </form>
  </section>;
}
