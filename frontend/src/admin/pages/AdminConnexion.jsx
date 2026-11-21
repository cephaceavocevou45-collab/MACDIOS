import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAdminAuth } from "../AdminAuthContext";
import { erreurAdmin } from "../adminApi";
import { SelecteurLangue, TexteLocalise, traduire } from "../../contexte/LangueContext";
import Icon from "../../composants/Icon";
import { branding } from "../../config/branding";

export default function AdminConnexion() {
  const { connexion, connecte } = useAdminAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);
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
      // Pour une réponse HTTP, afficher le message français de l’API plutôt
      // que le message technique Axios (« Request failed with status code… »).
      const message = error?.response || error?.code
        ? erreurAdmin(error)
        : error?.message || erreurAdmin(error);
      setErreur(traduire(message));
    } finally {
      setChargement(false);
    }
  };

  return (
    <main className="admin-login-page">
      <section className="admin-login-card">
        <div className="admin-login-locale"><SelecteurLangue compact /></div>
        <div className="admin-brand admin-brand-login">
          <span className="admin-brand-mark">{branding.logoMark}</span>
          <span>{branding.appName}<small><TexteLocalise phrase="BACK-OFFICE" /></small></span>
        </div>
        <div className="admin-login-kicker"><TexteLocalise phrase="ESPACE DE GESTION" /></div>
        <h1><TexteLocalise phrase="Connexion administrateur" /></h1>
        <p><TexteLocalise phrase="Connectez-vous avec votre compte admin ou sous-admin." /></p>
        {erreur && <div className="admin-alert admin-alert-error" role="alert">{erreur}</div>}
        <form onSubmit={envoyer} className="admin-form">
          <label>
            <TexteLocalise phrase="Email" />
            <input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder={traduire("nom@exemple.com")} />
          </label>
          <label>
            <TexteLocalise phrase="Mot de passe" />
            <span className="admin-password-wrap">
              <input type={motDePasseVisible ? "text" : "password"} autoComplete="current-password" required value={motDePasse} onChange={(event) => setMotDePasse(event.target.value)} placeholder={traduire("Votre mot de passe")} />
              <button
                type="button"
                className="password-visibility-toggle"
                aria-label={traduire(motDePasseVisible ? "Masquer le mot de passe" : "Afficher le mot de passe")}
                aria-pressed={motDePasseVisible}
                onClick={() => setMotDePasseVisible((visible) => !visible)}
              >
                <Icon name={motDePasseVisible ? "eyeOff" : "eye"} size={19} />
              </button>
            </span>
          </label>
          <button className="admin-button admin-button-primary admin-button-full" disabled={chargement}>
            {chargement ? "Connexion…" : "Se connecter"}
          </button>
        </form>
        <footer><TexteLocalise phrase="Accès réservé aux comptes d’administration autorisés." /></footer>
      </section>
    </main>
  );
}
