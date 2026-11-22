import axios from "axios";
import { traduire } from "./contexte/LangueContext";

// En production, l'API passe par Nginx sur le même domaine ; en local Vite vise Django.
const baseURL = (import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000"))
  .replace(/\/$/, "");
const requetesIdempotentesEnAttente = new Map();

// Efface une seule fois les anciens JWT stockés avant le passage aux cookies HttpOnly.
for (const cle of ["access", "refresh", "admin_access", "admin_refresh"]) {
  localStorage.removeItem(cle);
}

export const api = axios.create({
  baseURL,
  timeout: 20000,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

let jetonCSRF = "";

export async function initialiserCSRF() {
  const { data } = await api.get("/api/auth/csrf/");
  jetonCSRF = data.csrfToken || "";
}

api.interceptors.request.use((config) => {
  config.withCredentials = true;
  const methode = (config.method || "get").toLowerCase();
  if (jetonCSRF && !["get", "head", "options"].includes(methode)) {
    config.headers["X-CSRFToken"] = jetonCSRF;
  }

  // Réutilise une clé en mémoire si l'utilisateur renvoie la même opération
  // après un délai réseau. Aucune donnée financière n'est persistée côté client.
  const url = config.url || "";
  const estOperationFinanciere = methode === "post" && ["/api/ventes/", "/api/dettes/", "/api/paiements/"]
    .some((route) => url.startsWith(route));
  if (estOperationFinanciere && !config.headers["Idempotency-Key"]) {
    let donnees = config.data;
    if (typeof donnees === "string") {
      try { donnees = JSON.parse(donnees); } catch { /* Empreinte du texte brut ci-dessous. */ }
    }
    const normaliser = (valeur) => {
      if (Array.isArray(valeur)) return valeur.map(normaliser);
      if (valeur && typeof valeur === "object") {
        return Object.fromEntries(Object.keys(valeur).sort().map((cle) => [cle, normaliser(valeur[cle])]));
      }
      return valeur;
    };
    const signature = `${url}:${JSON.stringify(normaliser(donnees))}`;
    let cle = requetesIdempotentesEnAttente.get(signature);
    if (!cle) {
      cle = globalThis.crypto?.randomUUID?.()
        || `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
      requetesIdempotentesEnAttente.set(signature, cle);
    }
    config.headers["Idempotency-Key"] = cle;
    config._macdiosSignatureIdempotence = signature;
  }
  return config;
});

let renouvellementEnCours = null;

function terminerSession() {
  requetesIdempotentesEnAttente.clear();
  localStorage.removeItem("commercant");
  window.dispatchEvent(new Event("session-expiree"));
}

function terminerCleIdempotence(config, succes) {
  const signature = config?._macdiosSignatureIdempotence;
  if (!signature) return;
    const code = config._macdiosCodeErreur;
  // En cas de coupure ou d'erreur serveur, garder la clé pour sécuriser l'essai suivant.
  if (succes || (code >= 400 && code < 500 && code !== 429 && code !== 401)) {
    requetesIdempotentesEnAttente.delete(signature);
  }
}

export function viderRequetesIdempotentesEnAttente() {
  requetesIdempotentesEnAttente.clear();
}

api.interceptors.response.use(
  (reponse) => {
    terminerCleIdempotence(reponse.config, true);
    return reponse;
  },
  async (erreur) => {
    const requete = erreur.config;
    if (requete) requete._macdiosCodeErreur = erreur.response?.status;
    if (erreur.response?.status === 503 && erreur.response?.data?.code === "maintenance_active") {
      window.dispatchEvent(new CustomEvent("maintenance-active", { detail: erreur.response.data }));
    }
    const estRouteAuth = (requete?.url?.includes("/api/auth/") && !requete?.url?.includes("/api/auth/session/"))
      || requete?.url?.includes("/api/admin/auth/");
    if (erreur.response?.status !== 401 || !requete || requete._retentee || estRouteAuth) {
      terminerCleIdempotence(requete, false);
      return Promise.reject(erreur);
    }

    requete._retentee = true;
    try {
      // Les requêtes simultanées attendent le même rafraîchissement JWT.
      if (!renouvellementEnCours) {
        renouvellementEnCours = axios
          .post(`${baseURL}/api/auth/refresh/`, {}, {
            timeout: 20000, withCredentials: true,
            headers: jetonCSRF ? { "X-CSRFToken": jetonCSRF } : {},
          })
          .then(() => true)
          .finally(() => { renouvellementEnCours = null; });
      }
      await renouvellementEnCours;
      return api(requete);
    } catch (erreurRefresh) {
      terminerSession();
      terminerCleIdempotence(requete, false);
      return Promise.reject(erreurRefresh);
    }
  },
);

export function messageErreur(erreur) {
  const donnees = erreur?.response?.data;
  const typeContenu = String(erreur?.response?.headers?.["content-type"] || "").toLowerCase();
  const reponseHtml = typeContenu.includes("text/html")
    || (typeof donnees === "string" && /<!doctype\s+html|<html\b/i.test(donnees));
  if (reponseHtml) {
    if ((erreur.response?.status || 0) >= 500) {
      return traduire("Le serveur rencontre un problème. Réessayez dans quelques instants.");
    }
    if (erreur.response?.status === 403) {
      return traduire("La vérification de sécurité a échoué. Actualisez la page et réessayez.");
    }
    return traduire("Le serveur a renvoyé une réponse inattendue. Réessayez.");
  }
  if (typeof donnees === "string") return traduire(donnees);
  if (donnees && typeof donnees === "object") {
    const premiere = Object.values(donnees)[0];
    if (Array.isArray(premiere)) return traduire(String(premiere[0]));
    if (typeof premiere === "string") return traduire(premiere);
  }
  if (erreur?.code === "ECONNABORTED") return traduire("La connexion est lente. Réessayez.");
  if (!erreur?.response) return traduire("Serveur inaccessible. Vérifiez votre connexion internet.");
  return traduire("Une erreur est survenue. Réessayez.");
}
