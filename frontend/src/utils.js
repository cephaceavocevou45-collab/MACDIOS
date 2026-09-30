export function formaterFCFA(valeur) {
  const montant = Number(valeur || 0);
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(montant)} FCFA`;
}

export const FORMAT_TELEPHONE_BENIN = /^\+229[0-9]{8}$/;

export function telephoneBeninoisValide(valeur) {
  return FORMAT_TELEPHONE_BENIN.test(valeur);
}

export function extraireListe(reponse) {
  // Tolère une liste DRF classique et une éventuelle réponse paginée.
  return Array.isArray(reponse) ? reponse : reponse?.results || [];
}

export function afficherDate(date) {
  if (!date) return "";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(new Date(date));
}
