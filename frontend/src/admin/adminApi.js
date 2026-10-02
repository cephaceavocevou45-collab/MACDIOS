import { api } from "../api";

// Le back-office partage l'API à cookies HttpOnly, sans copie de JWT en stockage web.
export const adminApi = api;

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
