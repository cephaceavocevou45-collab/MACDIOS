import axios from "axios";

// L'URL vient de .env ; sans valeur, on utilise le serveur Django local.
const baseURL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export const api = axios.create({
  baseURL,
  timeout: 20000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const access = localStorage.getItem("access");
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let renouvellementEnCours = null;

function terminerSession() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("commercant");
  window.dispatchEvent(new Event("session-expiree"));
}

api.interceptors.response.use(
  (reponse) => reponse,
  async (erreur) => {
    const requete = erreur.config;
    const estRouteAuth = requete?.url?.includes("/api/auth/");
    if (erreur.response?.status !== 401 || !requete || requete._retentee || estRouteAuth) {
      return Promise.reject(erreur);
    }

    const refresh = localStorage.getItem("refresh");
    if (!refresh) {
      terminerSession();
      return Promise.reject(erreur);
    }

    requete._retentee = true;
    try {
      // Les requêtes simultanées attendent le même rafraîchissement JWT.
      if (!renouvellementEnCours) {
        renouvellementEnCours = axios
          .post(`${baseURL}/api/auth/refresh/`, { refresh }, { timeout: 20000 })
          .then(({ data }) => {
            localStorage.setItem("access", data.access);
            return data.access;
          })
          .finally(() => { renouvellementEnCours = null; });
      }
      const nouvelAccess = await renouvellementEnCours;
      requete.headers = requete.headers || {};
      requete.headers.Authorization = `Bearer ${nouvelAccess}`;
      return api(requete);
    } catch (erreurRefresh) {
      terminerSession();
      return Promise.reject(erreurRefresh);
    }
  },
);

export function messageErreur(erreur) {
  const donnees = erreur?.response?.data;
  if (typeof donnees === "string") return donnees;
  if (donnees && typeof donnees === "object") {
    const premiere = Object.values(donnees)[0];
    if (Array.isArray(premiere)) return String(premiere[0]);
    if (typeof premiere === "string") return premiere;
  }
  if (erreur?.code === "ECONNABORTED") return "La connexion est lente. Réessayez.";
  if (!erreur?.response) return "Serveur inaccessible. Vérifiez votre connexion internet.";
  return "Une erreur est survenue. Réessayez.";
}
