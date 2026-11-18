import { useLocation, useNavigate } from "react-router-dom";
import { TexteLocalise } from "../contexte/LangueContext";

// Revient à l’écran précédent, y compris à la page d’origine mémorisée par le footer.
export default function RetourPage() {
  const naviguer = useNavigate();
  const { state } = useLocation();

  return <button className="btn-ghost page-back-button" type="button" onClick={() => naviguer(state?.retourVers || -1)}>
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5m7 7-7-7 7-7"/>
    </svg>
    <TexteLocalise phrase="Retour" />
  </button>;
}
