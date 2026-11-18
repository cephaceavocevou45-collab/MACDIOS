import { useEffect } from "react";
import Icon from "./Icon";
import { traduire } from "../contexte/LangueContext";

export default function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return undefined;
    const fermerAvecEchap = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", fermerAvecEchap);
    return () => window.removeEventListener("keydown", fermerAvecEchap);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-panel" role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-header"><h2>{title}</h2><button className="icon-button" aria-label={traduire("Fermer")} onClick={onClose}><Icon name="close" /></button></header>
        <div className="modal-content">{children}</div>
      </section>
    </div>
  );
}
