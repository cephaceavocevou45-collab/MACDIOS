import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function VerifierDocument() {
  const { code } = useParams();
  const [etat, setEtat] = useState("chargement");
  const [dateGeneration, setDateGeneration] = useState(null);
  const [urlPdf, setUrlPdf] = useState("");
  const [erreurPdf, setErreurPdf] = useState(false);

  useEffect(() => {
    let actif = true;
    let urlCree = "";
    api.get(`/api/verifier/${encodeURIComponent(code)}/`)
      .then(async ({ data }) => {
        if (!actif) return;
        if (data.valide && data.date_generation) {
          setDateGeneration(new Intl.DateTimeFormat("fr-FR", {
            dateStyle: "long",
            timeStyle: "short",
            timeZone: "Africa/Porto-Novo",
          }).format(new Date(data.date_generation)));
          setEtat("valide");
          try {
            // Le PDF complet n'est demandé qu'après confirmation du code public.
            const pdf = await api.get(`/api/verifier/${encodeURIComponent(code)}/recu/`, { responseType: "blob" });
            urlCree = URL.createObjectURL(pdf.data);
            if (actif) setUrlPdf(urlCree);
            else URL.revokeObjectURL(urlCree);
          } catch {
            if (actif) setErreurPdf(true);
          }
        } else {
          setEtat("invalide");
        }
      })
      .catch(() => {
        if (actif) setEtat("invalide");
      });
    return () => {
      actif = false;
      if (urlCree) URL.revokeObjectURL(urlCree);
    };
  }, [code]);

  let message = "Vérification en cours…";
  if (etat === "valide") message = `Document authentique, généré le ${dateGeneration}`;
  if (etat === "invalide") message = "Code invalide";

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl bg-surface px-4 py-10 text-center text-lg font-semibold text-ink sm:px-6" role="status" aria-live="polite">
      <p className="mb-6">{message}</p>
      {etat === "valide" && <section aria-label="Reçu certifié" className="space-y-4">
        {urlPdf ? <>
          <a className="btn-primary inline-flex" href={urlPdf} target="_blank" rel="noreferrer">Ouvrir ou télécharger le reçu PDF</a>
          <iframe className="h-[78vh] min-h-[520px] w-full rounded-xl border border-line bg-white" src={urlPdf} title="Reçu certifié Nobi" />
        </> : erreurPdf
          ? <p className="text-sm font-medium text-red-700">Le code est valide, mais le reçu PDF ne peut pas être chargé. Réessayez dans quelques instants.</p>
          : <p className="text-sm font-medium text-ink-muted">Chargement du reçu complet…</p>}
      </section>}
    </main>
  );
}
