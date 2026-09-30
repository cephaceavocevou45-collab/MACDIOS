import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAdminAuth } from "../AdminAuthContext";
import { erreurAdmin } from "../adminApi";

export default function AdminConnexion() {
  const { connexion, connecte } = useAdminAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);

  if (connecte) return <Navigate to="/admin" replace/>;

  const envoyer = async (event) => {
    event.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      await connexion(email, motDePasse);
      navigate("/admin", { replace: true });
    } catch (error) {
      setErreur(error.message || erreurAdmin(error));
    } finally {
      setChargement(false);
    }
  };

  return <main className="admin-login-page"><section className="admin-login-card"><div className="admin-brand admin-brand-login"><span className="admin-brand-mark">N</span><span>Nobi<small>BACK-OFFICE</small></span></div><div className="admin-login-kicker">ESPACE DE GESTION</div><h1>Connexion administrateur</h1><p>Connectez-vous avec votre compte admin ou sous-admin.</p>{erreur && <div className="admin-alert admin-alert-error" role="alert">{erreur}</div>}<form onSubmit={envoyer} className="admin-form"><label>Email<input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nom@exemple.com"/></label><label>Mot de passe<input type="password" autoComplete="current-password" required value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} placeholder="Votre mot de passe"/></label><button className="admin-button admin-button-primary admin-button-full" disabled={chargement}>{chargement ? "Connexion…" : "Se connecter"}</button></form><footer>Accès réservé aux comptes d’administration autorisés.</footer></section></main>;
}
