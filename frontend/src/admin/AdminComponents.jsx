
import { localePourLangue, TexteLocalise, traduire } from "../contexte/LangueContext";export function AdminTitre({ surtitre = "NOBI · ADMINISTRATION", titre, description, action }) {
  return <header className="admin-page-head"><div><div className="admin-eyebrow">{traduire(surtitre)}</div><h1>{traduire(titre)}</h1>{description && <p>{traduire(description)}</p>}</div>{action && <div className="admin-head-action">{action}</div>}</header>;
}

export function AdminErreur({ children }) {
  return children ? <div className="admin-alert admin-alert-error" role="alert">{traduire(children)}</div> : null;
}

export function AdminEtatVide({ children = "Aucun résultat pour ces critères." }) {
  return <div className="admin-empty">{traduire(children)}</div>;
}

export function AdminChargement() {
  return <div className="admin-loading" aria-label={traduire("Chargement")}><i/><i/><i/></div>;
}

export function AdminPagination({ page, setPage, count, pageSize = 20 }) {
  const pages = Math.max(1, Math.ceil((count || 0) / pageSize));
  return <div className="admin-pagination"><span>{count || 0}{' '}{<TexteLocalise phrase={"résultat"} />}{count === 1 ? "" : "s"}{' '}{<TexteLocalise phrase={"· page"} />}{' '}{page}{' '}{<TexteLocalise phrase={"sur"} />}{' '}{pages}</span><div><button disabled={page <= 1} onClick={() => setPage(page - 1)}>{<TexteLocalise phrase={"Précédent"} />}</button><button disabled={page >= pages} onClick={() => setPage(page + 1)}>{<TexteLocalise phrase={"Suivant"} />}</button></div></div>;
}

export function AdminStat({ label, valeur, note, accent = "blue" }) {
  const correspondanceComptes = typeof note === "string" ? note.match(/^sur (\d+) comptes$/) : null;
  const noteTraduit = correspondanceComptes
    ? traduire("sur {count} comptes").replace("{count}", correspondanceComptes[1])
    : traduire(note);
  return <article className={`admin-stat admin-stat-${accent}`}><span>{traduire(label)}</span><strong>{valeur ?? "—"}</strong>{note && <small>{noteTraduit}</small>}</article>;
}

export function formatFcfa(value) {
  const number = Number(value || 0);
  return `${new Intl.NumberFormat(localePourLangue(), { maximumFractionDigits: 0 }).format(number)} FCFA`;
}

export function formatDate(value, heure = false) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(localePourLangue(), heure ? { dateStyle: "short", timeStyle: "short" } : { dateStyle: "medium" }).format(new Date(value));
}

export function AdminBadge({ children, tone = "neutral" }) {
  return <span className={`admin-badge admin-badge-${tone}`}>{traduire(children)}</span>;
}

export function AdminModal({ titre, children, onClose }) {
  return <div className="admin-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="admin-dialog-title"><header><h2 id="admin-dialog-title">{traduire(titre)}</h2><button type="button" className="admin-icon-button" onClick={onClose} aria-label={traduire("Fermer")}>×</button></header>{children}</section></div>;
}

export const PERMISSIONS_ADMIN = [
  ["voir_utilisateurs", "Voir les commerçants"],
  ["suspendre_utilisateur", "Suspendre ou réactiver un commerçant"],
  ["valider_paiements", "Valider les paiements"],
  ["voir_audit", "Consulter le journal d’audit"],
  ["voir_statistiques", "Voir les statistiques"],
];
