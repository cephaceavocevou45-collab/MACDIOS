import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "./contexte/AuthContext";
import { ToastProvider } from "./composants/ToastProvider";
import MiseEnPage from "./composants/MiseEnPage";
import ProtectionRoute from "./composants/ProtectionRoute";
import AccueilPublique from "./pages/AccueilPublique";
import Clients from "./pages/Clients";
import Connexion from "./pages/Connexion";
import DetailClient from "./pages/DetailClient";
import HistoriqueVentes from "./pages/HistoriqueVentes";
import Inscription from "./pages/Inscription";
import NouvelleVente from "./pages/NouvelleVente";
import Produits from "./pages/Produits";
import TableauDeBord from "./pages/TableauDeBord";
import Abonnement from "./pages/Abonnement";
import HistoriqueActivite from "./pages/HistoriqueActivite";
import PageLegale from "./pages/PageLegale";
import DonneesCompte from "./pages/DonneesCompte";
import MotDePasseOublie from "./pages/MotDePasseOublie";
import NouveauMotDePasse from "./pages/NouveauMotDePasse";
import VerifierDocument from "./pages/VerifierDocument";
import MonProfil from "./pages/MonProfil";
import ContactezNous from "./pages/ContactezNous";
import AdminRoutes from "./admin/AdminRoutes";
import FooterApplication from "./composants/FooterApplication";
import Parametres from "./pages/Parametres";
import Fournisseurs from "./pages/Fournisseurs";
import Approvisionnements from "./pages/Approvisionnements";
import MouvementsStock from "./pages/MouvementsStock";
import { api } from "./api";
import { branding } from "./config/branding";
import { LangueProvider, TexteLocalise, useLangue } from "./contexte/LangueContext";


function PageAvecPiedDePage({ children }) {
  return <div className="page-with-footer">{children}<FooterApplication/></div>;
}

function Racine() {
  const { connecte } = useAuth();
  return connecte ? <Navigate to="/tableau-de-bord" replace/> : <AccueilPublique/>;
}

function InvitationInstallation() {
  const [invite, setInvite] = useState(null);
  const [instructionsIOS, setInstructionsIOS] = useState(false);
  const [masquee, setMasquee] = useState(false);
  const estIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
    && !window.matchMedia?.("(display-mode: standalone)").matches
    && !navigator.standalone;

  useEffect(() => {
    const proposer = (event) => {
      event.preventDefault();
      setInvite(event);
    };
    const installee = () => { setInvite(null); setInstructionsIOS(false); };
    window.addEventListener("beforeinstallprompt", proposer);
    window.addEventListener("appinstalled", installee);
    return () => {
      window.removeEventListener("beforeinstallprompt", proposer);
      window.removeEventListener("appinstalled", installee);
    };
  }, []);

  if (masquee || (!invite && !estIOS)) return null;

  async function installer() {
    if (invite) {
      await invite.prompt();
      await invite.userChoice;
      setInvite(null);
    } else {
      setInstructionsIOS((visible) => !visible);
    }
  }

  return <aside className="pwa-install-card" aria-label="Installer l’application">
    <div className="pwa-install-copy">
      <strong>Utilisez l’application plus facilement</strong>
      {instructionsIOS && <span>Dans Safari, touchez Partager puis « Sur l’écran d’accueil ».</span>}
    </div>
    <button type="button" className="pwa-install-action" onClick={installer}>
      {estIOS ? "Comment installer" : "Installer"}
    </button>
    <button type="button" className="pwa-install-close" aria-label="Fermer" onClick={() => setMasquee(true)}>×</button>
  </aside>;
}

function PageIntrouvable() {
  return <PageAvecPiedDePage><main className="mx-auto min-h-screen max-w-md flex-1 space-y-4 px-5 py-16 text-center"><h1 className="text-2xl font-bold">{<TexteLocalise phrase={"Page introuvable"} />}</h1><Link to="/" className="font-semibold text-brand">{<TexteLocalise phrase={"Retour à l’accueil"} />}</Link></main></PageAvecPiedDePage>;
}

function EcranMaintenance({ message, verifier, verification }) {
  return <main className="maintenance-screen">
    <div className="maintenance-card">
      <span className="brand-lockup"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</span>
      <span className="maintenance-icon" aria-hidden="true">⚙</span>
      <p className="form-eyebrow">{<TexteLocalise phrase={"Interruption temporaire"} />}</p>
      <h1>{<TexteLocalise phrase={"Maintenance en cours"} />}</h1>
      <p className="maintenance-message">{message}</p>
      <p className="maintenance-hint">{<TexteLocalise phrase={"Vos données restent protégées. Réessayez dans quelques instants."} />}</p>
      <button className="btn-primary" type="button" onClick={verifier} disabled={verification}>{verification ? <TexteLocalise phrase={"Vérification en cours…"} /> : <TexteLocalise phrase={"Vérifier à nouveau"} />}</button>
    </div>
  </main>;
}

function MaintenanceGate({ children }) {
  const { pathname } = useLocation();
  const [etat, setEtat] = useState({ actif: false, message: "" });
  const [verification, setVerification] = useState(false);

  useEffect(() => {
    let vivant = true;
    const recevoirMaintenance = (event) => setEtat({ actif: true, message: event.detail?.detail || "" });
    window.addEventListener("maintenance-active", recevoirMaintenance);
    api.get("/api/maintenance/")
      .then(({ data }) => { if (vivant) setEtat(data); })
      .catch(() => { /* L'indisponibilité du service n'est pas confondue avec une maintenance annoncée. */ });
    return () => { vivant = false; window.removeEventListener("maintenance-active", recevoirMaintenance); };
  }, []);

  const verifier = async () => {
    setVerification(true);
    try {
      const { data } = await api.get("/api/maintenance/");
      setEtat(data);
    } catch { /* Le message de maintenance reste visible en cas d'échec réseau. */ }
    finally { setVerification(false); }
  };

  if (etat.actif && !pathname.startsWith("/admin")) {
    return <EcranMaintenance message={etat.message} verifier={verifier} verification={verification}/>;
  }
  return children;
}

function RoutesApplication() {
  const { langue } = useLangue();
  return <div className="locale-racine" data-langue={langue}><BrowserRouter><MaintenanceGate><Routes>
      <Route path="/" element={<Racine/>}/>
      <Route path="/contact" element={<PageAvecPiedDePage><ContactezNous/></PageAvecPiedDePage>}/>
      <Route path="/connexion" element={<PageAvecPiedDePage><Connexion/></PageAvecPiedDePage>}/>
      <Route path="/inscription" element={<PageAvecPiedDePage><Inscription/></PageAvecPiedDePage>}/>
      <Route path="/mot-de-passe-oublie" element={<PageAvecPiedDePage><MotDePasseOublie/></PageAvecPiedDePage>}/>
      <Route path="/nouveau-mot-de-passe" element={<PageAvecPiedDePage><NouveauMotDePasse/></PageAvecPiedDePage>}/>
      <Route path="/verifier/:code" element={<PageAvecPiedDePage><VerifierDocument/></PageAvecPiedDePage>}/>
      <Route path="/conditions" element={<PageAvecPiedDePage><PageLegale type="conditions"/></PageAvecPiedDePage>}/>
      <Route path="/confidentialite" element={<PageAvecPiedDePage><PageLegale type="confidentialite"/></PageAvecPiedDePage>}/>
      <Route path="/admin/*" element={<AdminRoutes/>}/>
      <Route element={<ProtectionRoute/>}><Route element={<MiseEnPage/>}>
        <Route path="/tableau-de-bord" element={<TableauDeBord/>}/>
        <Route path="/produits" element={<Produits/>}/>
        <Route path="/fournisseurs" element={<Fournisseurs/>}/>
        <Route path="/approvisionnements" element={<Approvisionnements/>}/>
        <Route path="/mouvements-stock" element={<MouvementsStock/>}/>
        <Route path="/ventes/nouvelle" element={<NouvelleVente/>}/>
        <Route path="/ventes/historique" element={<HistoriqueVentes/>}/>
        <Route path="/clients" element={<Clients/>}/>
        <Route path="/clients/:id" element={<DetailClient/>}/>
        <Route path="/abonnement" element={<Abonnement/>}/>
        <Route path="/activite" element={<HistoriqueActivite/>}/>
        <Route path="/compte/donnees" element={<DonneesCompte/>}/>
        <Route path="/profil" element={<MonProfil/>}/>
        <Route path="/parametres" element={<Parametres/>}/>
      </Route></Route>
      <Route path="*" element={<PageIntrouvable/>}/>
    </Routes></MaintenanceGate></BrowserRouter></div>;
}

export default function App() {
  return <LangueProvider><AuthProvider><ToastProvider><RoutesApplication/><InvitationInstallation/></ToastProvider></AuthProvider></LangueProvider>;
}
