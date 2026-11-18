import Button from "./Button";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

/** Commandes simples de navigation pour les listes paginées du serveur. */
export default function Pagination({ page, count, pageSize = 20, onChange }) {
  const pages = Math.max(1, Math.ceil((count || 0) / pageSize));
  if (pages <= 1) return null;
  return <nav className="my-5 flex items-center justify-center gap-3" aria-label={traduire("Pagination")}>
    <Button variant="secondary" size="small" disabled={page <= 1} onClick={() => onChange(page - 1)}>{<TexteLocalise phrase={"Précédent"} />}</Button>
    <span className="text-sm text-ink-muted" aria-live="polite">{<TexteLocalise phrase={"Page"} />}{' '}{page}{' '}{<TexteLocalise phrase={"sur"} />}{' '}{pages} · {count}{' '}{<TexteLocalise phrase={"éléments"} />}</span>
    <Button variant="secondary" size="small" disabled={page >= pages} onClick={() => onChange(page + 1)}>{<TexteLocalise phrase={"Suivant"} />}</Button>
  </nav>;
}
