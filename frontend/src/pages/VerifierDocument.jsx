import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function VerifierDocument() {
  const { code } = useParams();
  const [etat, setEtat] = useState("chargement");
  const [dateGeneration, setDateGeneration] = useState(null);

  useEffect(() => {
    let actif = true;
    api.get(`/api/verifier/${encodeURIComponent(code)}/`)
      .then(({ data }) => {
        if (!actif) return;
        if (data.valide && data.date_generation) {
          setDateGeneration(new Intl.DateTimeFormat("fr-FR", {
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
  }, [code]);

  let message = "Vérification en cours…";
  if (etat === "valide") message = `Document authentique, généré le ${dateGeneration}`;
  if (etat === "invalide") message = "Code invalide";

  // La page publique ne révèle que l'authenticité et la date du document.
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl items-center justify-center bg-surface px-4 py-10 text-center text-lg font-semibold text-ink sm:px-6" role="status" aria-live="polite">
      <p>{message}</p>
    </main>
  );
}
