import { useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminErreur, AdminStat, AdminTitre, formatFcfa } from "../AdminComponents";
import { useAdminAuth, aPermission } from "../AdminAuthContext";

export default function AdminDashboard() {
  const { administrateur } = useAdminAuth();
  const [stats, setStats] = useState(null);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    let actif = true;
    adminApi.get("/api/admin/statistiques/").then(({ data }) => { if (actif) setStats(data); })
      .catch((error) => { if (actif) setErreur(erreurAdmin(error)); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, []);

  const voir = (key) => !chargement && stats && aPermission(administrateur, "voir_statistiques") && <AdminStat {...key}/>;

  return <><AdminTitre titre="Vue d’ensemble" description="Indicateurs clés de l’activité sur toute la plateforme."/><AdminErreur>{erreur}</AdminErreur>{chargement ? <div className="admin-stat-grid">{Array.from({ length: 5 }, (_, i) => <div className="admin-stat admin-stat-skeleton" key={i}/>)}</div> : stats && <div className="admin-stat-grid">
    {voir({ label: "Commerçants actifs", valeur: stats.commercants_actifs, note: `sur ${stats.nombre_commercants} comptes`, accent: "green" })}
    {voir({ label: "En période d’essai", valeur: stats.commercants_en_essai, note: "abonnements d’essai actifs", accent: "amber" })}
    {voir({ label: "Abonnements expirés", valeur: stats.commercants_expires, note: "accès en lecture seule", accent: "slate" })}
    {voir({ label: "Revenus du mois", valeur: formatFcfa(stats.revenus_mois), note: "paiements confirmés", accent: "blue" })}
    {voir({ label: "Ventes enregistrées", valeur: stats.ventes_enregistrees, note: "sur toute la plateforme", accent: "violet" })}
    {voir({ label: "Revenus totaux", valeur: formatFcfa(stats.revenus_totaux), note: "depuis le lancement", accent: "blue" })}
    {voir({ label: "Dettes en cours", valeur: formatFcfa(stats.dettes_en_cours), note: "solde cumulé des clients", accent: "rose" })}
  </div>}</>;
}
