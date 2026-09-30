import axios from "axios";

const baseURL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

// Session indépendante pour éviter de remplacer les identifiants du commerçant.
export const adminApi = axios.create({
  baseURL,
  timeout: 20000,
  headers: { "Content-Type": "application/json" },
});

adminApi.interceptors.request.use((config) => {
  const access = localStorage.getItem("admin_access");
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshEnCours = null;

function fermerSessionAdmin() {
  localStorage.removeItem("admin_access");
  localStorage.removeItem("admin_refresh");
  localStorage.removeItem("administrateur");
  window.dispatchEvent(new Event("admin-session-expiree"));
}

adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requete = error.config;
    if (error.response?.status !== 401 || !requete || requete._retentee || requete.url?.includes("/auth/connexion/")) {
      return Promise.reject(error);
    }
    const refresh = localStorage.getItem("admin_refresh");
    if (!refresh) {
      fermerSessionAdmin();
      return Promise.reject(error);
    }
    requete._retentee = true;
    try {
      if (!refreshEnCours) {
        refreshEnCours = axios.post(`${baseURL}/api/auth/refresh/`, { refresh }, { timeout: 20000 })
          .then(({ data }) => {
            localStorage.setItem("admin_access", data.access);
            return data.access;
          })
          .finally(() => { refreshEnCours = null; });
      }
      requete.headers = requete.headers || {};
      requete.headers.Authorization = `Bearer ${await refreshEnCours}`;
      return adminApi(requete);
    } catch (refreshError) {
      fermerSessionAdmin();
      return Promise.reject(refreshError);
    }
  },
);

export function erreurAdmin(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (typeof first === "string") return first;
  }
  if (error?.code === "ECONNABORTED") return "La connexion est lente. Réessayez.";
  return error?.response ? "Une erreur est survenue. Vérifiez les informations." : "Serveur inaccessible. Vérifiez votre connexion.";
}
