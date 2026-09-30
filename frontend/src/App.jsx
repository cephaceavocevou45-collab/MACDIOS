import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
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
import AdminRoutes from "./admin/AdminRoutes";
import FooterApplication from "./composants/FooterApplication";

function PageAvecPiedDePage({ children }) {
  return <div className="page-with-footer">{children}<FooterApplication/></div>;
}

function Racine() {
  const { connecte } = useAuth();
  return connecte ? <Navigate to="/tableau-de-bord" replace/> : <AccueilPublique/>;
}

function PageIntrouvable() {
  return <PageAvecPiedDePage><main className="mx-auto min-h-screen max-w-md flex-1 space-y-4 px-5 py-16 text-center"><h1 className="text-2xl font-bold">Page introuvable</h1><Link to="/" className="font-semibold text-brand">Retour à l’accueil</Link></main></PageAvecPiedDePage>;
}

export default function App() {
  return (
    <AuthProvider><ToastProvider><BrowserRouter><Routes>
      <Route path="/" element={<Racine/>}/>
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
        <Route path="/ventes/nouvelle" element={<NouvelleVente/>}/>
        <Route path="/ventes/historique" element={<HistoriqueVentes/>}/>
        <Route path="/clients" element={<Clients/>}/>
        <Route path="/clients/:id" element={<DetailClient/>}/>
        <Route path="/abonnement" element={<Abonnement/>}/>
        <Route path="/activite" element={<HistoriqueActivite/>}/>
        <Route path="/compte/donnees" element={<DonneesCompte/>}/>
      </Route></Route>
      <Route path="*" element={<PageIntrouvable/>}/>
    </Routes></BrowserRouter></ToastProvider></AuthProvider>
  );
}
