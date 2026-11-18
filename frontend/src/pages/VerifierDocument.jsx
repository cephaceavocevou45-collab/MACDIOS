import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { localePourLangue, traduire, useLangue } from "../contexte/LangueContext";

export default function VerifierDocument() {
  const { langue } = useLangue();
  const { code } = useParams();
  const [etat, setEtat] = useState("chargement");
  const [dateGeneration, setDateGeneration] = useState(null);

  useEffect(() => {
    let actif = true;
    api.get(`/api/verifier/${encodeURIComponent(code)}/`)
      .then(({ data }) => {
        if (!actif) return;
        if (data.valide && data.date_generation) {
          setDateGeneration(new Intl.DateTimeFormat(localePourLangue(langue), {
            dateStyle: "long",
            timeStyle: "short",
            timeZone: "Africa/Porto-Novo",
          }).format(new Date(data.date_generation)));
          setEtat("valide");
        } else {
          setEtat("invalide");
        }
      })
      .catch(() => {
        if (actif) setEtat("invalide");
      });
    return () => { actif = false; };
  }, [code, langue]);

  let message = traduire("Vérification en cours…", langue);
  if (etat === "valide") message = `${traduire("Document authentique, généré le", langue)} ${dateGeneration}`;
  if (etat === "invalide") message = traduire("Code invalide", langue);

  // La page publique ne révèle que l'authenticité et la date du document.
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl items-center justify-center bg-surface px-4 py-10 text-center text-lg font-semibold text-ink sm:px-6" role="status" aria-live="polite">
      <p>{message}</p>
    </main>
  );
}
