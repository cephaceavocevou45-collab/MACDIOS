import Card from "../composants/Card";
import { branding } from "../config/branding";
import { TexteLocalise, traduire, useLangue } from "../contexte/LangueContext";
import RetourPage from "../composants/RetourPage";

const pages = {
  conditions: {
    titre: "Conditions d’utilisation",
    sections: [
      ["Objet", `${branding.appName} propose un outil de suivi des produits, des ventes, des clients et des dettes d’une boutique. Le service ne remplace pas les obligations comptables, fiscales ou réglementaires applicables à l’activité.`],
      ["Compte commerçant", "L’utilisateur fournit des informations exactes, protège ses identifiants et reste responsable des actions réalisées dans son compte. Il doit disposer des droits nécessaires pour saisir les données de ses clients."],
      ["Disponibilité et données", "Le service est fourni selon sa disponibilité. L’utilisateur reste responsable de ses justificatifs et peut exporter ou demander la suppression de son compte depuis les fonctions prévues."],
      ["Abonnement et paiements", "Les tarifs et durées applicables sont affichés dans l’application avant paiement. Un paiement manuel n’active l’abonnement qu’après vérification par l’administration."],
      ["Contact", `Pour toute question, contactez-nous au ${branding.contact.telephone} ou par WhatsApp. Les présentes conditions doivent être examinées et validées avant leur entrée en vigueur.`],
    ],
  },
  confidentialite: {
    titre: "Politique de confidentialité",
    sections: [
      ["Responsable du traitement", `${branding.appName} traite les informations nécessaires au fonctionnement du service. L’identité juridique de l’entité qui exploite le service et son adresse doivent être vérifiées et ajoutées avant publication.`],
      ["Données utilisées", "Le service traite l’adresse email du compte, le nom de la boutique et, si renseigné, le téléphone de contact, ainsi que les produits, ventes, clients, dettes et paiements saisis. Il conserve aussi les traces techniques nécessaires à la sécurité et au fonctionnement."],
      ["Finalités et accès", "Les données servent à fournir les fonctions de gestion, sécuriser les connexions, assurer le support et satisfaire aux obligations applicables. Les données d’une boutique ne sont pas accessibles aux autres commerçants."],
      ["Conservation et prestataires", "Les durées de conservation, les catégories de prestataires, les transferts éventuels et les mesures propres à chaque prestataire doivent être confirmés à partir de la configuration réelle du service et des règles applicables."],
      ["Droits", "Le commerçant peut exporter ses données et demander la suppression de son compte depuis l’application. Les éventuelles obligations légales de conservation doivent être vérifiées avant de traiter une demande de suppression."],
      ["Contact", `Pour toute question sur les données personnelles, contactez-nous au ${branding.contact.telephone} ou par WhatsApp.`],
    ],
  },
};

export default function PageLegale({ type }) {
  const { langue } = useLangue();
  const page = pages[type];
  const localiserTexteJuridique = (texte) => traduire(
    texte.replaceAll(branding.appName, "{app}").replaceAll(branding.contact.telephone, "{telephone}"),
    langue,
  ).replaceAll("{app}", branding.appName).replaceAll("{telephone}", branding.contact.telephone);
  return <main className="legal-page mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
    <RetourPage />
    <span className="form-eyebrow">{branding.appName}{' '}{<TexteLocalise phrase={"· Document juridique"} />}</span>
    <h1 className="mt-2 text-3xl font-bold">{traduire(page.titre, langue)}</h1>
    <div role="alert" className="my-6 rounded-xl border border-amber-300 bg-amber-50 p-4 font-bold text-amber-900">{<TexteLocalise phrase={"MODÈLE À FAIRE VALIDER PAR UN JURISTE"} />}</div>
    <div className="grid gap-4">{page.sections.map(([titre, texte]) => <Card key={titre}><h2 className="mb-2 mt-0 text-lg font-bold">{traduire(titre, langue)}</h2><p className="m-0 leading-7 text-ink-muted">{localiserTexteJuridique(texte)}</p></Card>)}</div>
    <p className="mt-6 text-sm text-ink-muted">{<TexteLocalise phrase={"Modèle de travail sans date d’entrée en vigueur. Les informations de l’entité et les obligations applicables doivent être confirmées avant publication."} />}</p>
  </main>;
}
