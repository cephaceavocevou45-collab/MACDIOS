import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AdminAuthProvider, aPermission, useAdminAuth } from "./AdminAuthContext";
import AdminLayout from "./AdminLayout";
import AdminConnexion from "./pages/AdminConnexion";
import AdminDashboard from "./pages/AdminDashboard";
import AdminUtilisateurs from "./pages/AdminUtilisateurs";
import AdminPaiements from "./pages/AdminPaiements";
import AdminAudit from "./pages/AdminAudit";
import AdminSousAdmins from "./pages/AdminSousAdmins";
import AdminOffreEssai from "./pages/AdminOffreEssai";
import FooterApplication from "../composants/FooterApplication";

function ConnexionAdminAvecPied() {
  return <div className="page-with-footer"><AdminConnexion/><FooterApplication/></div>;
}

function AdminGarde({ permission }) {
  const { connecte, administrateur, initialisation } = useAdminAuth();
  if (initialisation) return <div className="admin-loading" role="status">Vérification de la session…</div>;
  if (!connecte) return <Navigate to="/admin/connexion" replace/>;
  if (permission === "super_admin" && !administrateur?.super_admin) return <Navigate to="/admin" replace/>;
  if (permission && permission !== "super_admin" && !aPermission(administrateur, permission)) return <Navigate to="/admin" replace/>;
  return <Outlet/>;
}

function DestinationAdmin() {
  const { administrateur } = useAdminAuth();
  if (aPermission(administrateur, "voir_statistiques")) return <Navigate to="/admin/statistiques" replace/>;
  if (aPermission(administrateur, "voir_utilisateurs")) return <Navigate to="/admin/utilisateurs" replace/>;
  if (aPermission(administrateur, "valider_paiements")) return <Navigate to="/admin/paiements" replace/>;
  if (aPermission(administrateur, "voir_audit")) return <Navigate to="/admin/audit" replace/>;
  if (administrateur?.super_admin) return <Navigate to="/admin/sous-admins" replace/>;
  return <div className="admin-denied">Aucun accès de gestion n’est associé à ce compte.</div>;
}

function RoutesAdmin() {
  const { connecte, initialisation } = useAdminAuth();
  if (initialisation) return <div className="admin-loading" role="status">Vérification de la session…</div>;
  return <Routes>
    <Route path="connexion" element={connecte ? <DestinationAdmin/> : <ConnexionAdminAvecPied/>}/>
    <Route element={<AdminGarde/>}><Route element={<AdminLayout/>}>
      <Route index element={<DestinationAdmin/>}/>
      <Route element={<AdminGarde permission="voir_statistiques"/>}><Route path="statistiques" element={<AdminDashboard/>}/></Route>
      <Route element={<AdminGarde permission="voir_utilisateurs"/>}><Route path="utilisateurs" element={<AdminUtilisateurs/>}/></Route>
      <Route element={<AdminGarde permission="valider_paiements"/>}><Route path="paiements" element={<AdminPaiements/>}/></Route>
      <Route element={<AdminGarde permission="voir_audit"/>}><Route path="audit" element={<AdminAudit/>}/></Route>
      <Route element={<AdminGarde permission="super_admin"/>}><Route path="sous-admins" element={<AdminSousAdmins/>}/></Route>
      <Route element={<AdminGarde permission="super_admin"/>}><Route path="offre-essai" element={<AdminOffreEssai/>}/></Route>
    </Route></Route>
    <Route path="*" element={<Navigate to="/admin" replace/>}/>
  </Routes>;
}

export default function AdminRoutes() {
  return <AdminAuthProvider><RoutesAdmin/></AdminAuthProvider>;
}
