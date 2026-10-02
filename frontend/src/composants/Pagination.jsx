import Button from "./Button";

/** Commandes simples de navigation pour les listes paginées du serveur. */
export default function Pagination({ page, count, pageSize = 20, onChange }) {
  const pages = Math.max(1, Math.ceil((count || 0) / pageSize));
  if (pages <= 1) return null;
  return <nav className="my-5 flex items-center justify-center gap-3" aria-label="Pagination">
    <Button variant="secondary" size="small" disabled={page <= 1} onClick={() => onChange(page - 1)}>Précédent</Button>
    <span className="text-sm text-ink-muted" aria-live="polite">Page {page} sur {pages} · {count} éléments</span>
    <Button variant="secondary" size="small" disabled={page >= pages} onClick={() => onChange(page + 1)}>Suivant</Button>
  </nav>;
}
