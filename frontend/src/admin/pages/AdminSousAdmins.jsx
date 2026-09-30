import { useCallback, useEffect, useState } from "react";
import { adminApi, erreurAdmin } from "../adminApi";
import { AdminBadge, AdminChargement, AdminErreur, AdminEtatVide, AdminModal, AdminPagination, AdminTitre, PERMISSIONS_ADMIN, formatDate } from "../AdminComponents";

const vide = { email: "", nom: "", permissions: [] };

export default function AdminSousAdmins() {
  const [donnees, setDonnees] = useState({ results: [], count: 0 });
  const [page, setPage] = useState(1);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [invite, setInvite] = useState(false);
  const [cible, setCible] = useState(null);
  const [form, setForm] = useState(vide);
  const [enCours, setEnCours] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true); setErreur("");
    try { const { data } = await adminApi.get("/api/admin/sous-admins/", { params: { page } }); setDonnees(data); }
    catch (error) { setErreur(erreurAdmin(error)); }
    finally { setChargement(false); }
  }, [page]);
  useEffect(() => { charger(); }, [charger]);

  const ouvrirInvitation = () => { setForm(vide); setInvite(true); setCible(null); };
  const ouvrirModification = (profil) => { setForm({ email: profil.email, nom: profil.nom, permissions: [...profil.permissions] }); setCible(profil); setInvite(false); };
  const cocher = (permission) => setForm((actuel) => ({ ...actuel, permissions: actuel.permissions.includes(permission) ? actuel.permissions.filter((p) => p !== permission) : [...actuel.permissions, permission] }));
  const envoyer = async (event) => {
    event.preventDefault(); setErreur(""); setEnCours(true);
    try {
      if (cible) await adminApi.patch(`/api/admin/sous-admins/${cible.id}/`, { permissions: form.permissions });
      else await adminApi.post("/api/admin/sous-admins/", form);
      setInvite(false); setCible(null); await charger();
    } catch (error) { setErreur(erreurAdmin(error)); }
    finally { setEnCours(false); }
  };
  const basculerActif = async (profil) => {
    setErreur("");
    try { await adminApi.patch(`/api/admin/sous-admins/${profil.id}/`, { actif: !profil.actif }); await charger(); }
    catch (error) { setErreur(erreurAdmin(error)); }
  };

  return <><AdminTitre titre="Sous-admins" description="Invitez des personnes et attribuez leurs permissions une par une." action={<button className="admin-button admin-button-primary" onClick={ouvrirInvitation}>＋ Inviter un sous-admin</button>}/><AdminErreur>{erreur}</AdminErreur><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Nom</th><th>Email</th><th>Permissions</th><th>État</th><th>Invité le</th><th>Actions</th></tr></thead><tbody>{!chargement && donnees.results.map((profil) => <tr key={profil.id}><td><strong>{profil.nom}</strong></td><td>{profil.email}</td><td><div className="admin-permission-badges">{profil.permissions.length ? profil.permissions.map((p) => <AdminBadge key={p}>{PERMISSIONS_ADMIN.find(([key]) => key === p)?.[1] || p}</AdminBadge>) : <small>Aucun droit attribué</small>}</div></td><td><AdminBadge tone={profil.actif ? "green" : "red"}>{profil.actif ? "Actif" : "Désactivé"}</AdminBadge></td><td>{formatDate(profil.date_creation)}</td><td><div className="admin-row-actions"><button className="admin-button admin-button-secondary admin-button-small" onClick={() => ouvrirModification(profil)}>Droits</button><button className={`admin-button admin-button-small ${profil.actif ? "admin-button-danger" : "admin-button-primary"}`} onClick={() => basculerActif(profil)}>{profil.actif ? "Désactiver" : "Activer"}</button></div></td></tr>)}</tbody></table>{chargement ? <AdminChargement/> : donnees.results.length === 0 && <AdminEtatVide>Aucun sous-admin n’a encore été invité.</AdminEtatVide>}</div><AdminPagination page={page} setPage={setPage} count={donnees.count}/>
    {(invite || cible) && <AdminModal titre={invite ? "Inviter un sous-admin" : `Permissions · ${cible.nom}`} onClose={() => { setInvite(false); setCible(null); }}><form className="admin-form" onSubmit={envoyer}>{invite && <><label>Nom<input required maxLength="120" value={form.nom} onChange={(e) => setForm((s) => ({ ...s, nom: e.target.value }))}/></label><label>Email<input type="email" required maxLength="254" value={form.email} onChange={(e) => setForm((s) => ({ ...s, email: e.target.value }))}/></label><p className="admin-modal-copy">Une invitation avec un lien de création de mot de passe sera envoyée par email.</p></>}<fieldset className="admin-permission-list"><legend>Permissions à attribuer</legend>{PERMISSIONS_ADMIN.map(([key, label]) => <label key={key}><input type="checkbox" checked={form.permissions.includes(key)} onChange={() => cocher(key)}/><span>{label}</span></label>)}</fieldset><div className="admin-modal-actions"><button type="button" className="admin-button admin-button-secondary" onClick={() => { setInvite(false); setCible(null); }}>Annuler</button><button className="admin-button admin-button-primary" disabled={enCours}>{enCours ? "Enregistrement…" : invite ? "Envoyer l’invitation" : "Enregistrer les droits"}</button></div></form></AdminModal>}
  </>;
}
