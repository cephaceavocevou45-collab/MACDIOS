// Sentry reste totalement inactif et non téléchargé lorsque le DSN est vide.
const cleSensible = /password|mot.?de.?passe|token|authorization|secret|api.?key|telephone|phone|email|courriel/i;
const telephone = /(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)/g;
const email = /(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-z]{2,}(?![\w.-])/gi;
const jwt = /(?<![\w-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g;
const secretDansTexte = /(password|mot.?de.?passe|token|secret|api.?key)\s*[:=]\s*[^\s,;]+/gi;

function nettoyer(valeur) {
  if (Array.isArray(valeur)) return valeur.map(nettoyer);
  if (valeur && typeof valeur === "object") {
    return Object.fromEntries(Object.entries(valeur).map(([cle, contenu]) => [
      cle, cleSensible.test(cle) ? "[MASQUÉ]" : nettoyer(contenu),
    ]));
  }
  return typeof valeur === "string" ? valeur.replace(jwt, "[JETON MASQUÉ]").replace(secretDansTexte, "$1=[MASQUÉ]").replace(email, "[EMAIL MASQUÉ]").replace(telephone, "[NUMÉRO MASQUÉ]") : valeur;
}

export function initialiserSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;
  import("@sentry/react").then((Sentry) => Sentry.init({
    dsn,
    sendDefaultPii: false,
    beforeSend(event) {
      delete event.user;
      return nettoyer(event);
    },
  }));
}
