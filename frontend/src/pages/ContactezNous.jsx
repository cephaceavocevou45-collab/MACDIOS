import { useState } from "react";
import { branding } from "../config/branding";
import { TexteLocalise, traduire } from "../contexte/LangueContext";
import RetourPage from "../composants/RetourPage";

function IconeContact({ type }) {
  const icones = {
    email: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></>,
    whatsapp: <><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M9 8.5c.5 2 2 3.5 4.5 4.5l1-1 2 1-.5 2c-4 .7-8.8-4-8-8l2-.5 1 2-1 1Z"/></>,
    adresse: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{icones[type]}</svg>;
}

export default function ContactezNous() {
  const [erreur, setErreur] = useState("");
  const adresseEmail = branding.contact.email?.trim();
  const whatsapp = branding.contact.whatsapp?.trim();
  const numeroWhatsApp = whatsapp?.match(/wa\.me\/(\d+)/i)?.[1];

  function envoyer(event) {
    event.preventDefault();
    if (!adresseEmail) {
      setErreur("L’adresse de contact n’est pas configurée pour le moment.");
      return;
    }

    const formulaire = new FormData(event.currentTarget);
    const nom = String(formulaire.get("nom") || "").trim();
    const email = String(formulaire.get("email") || "").trim();
    const objet = String(formulaire.get("objet") || "").trim() || "Demande d’information";
    const message = String(formulaire.get("message") || "").trim();
    const contenu = `Nom : ${nom}\nAdresse email : ${email}\n\n${message}`;
    const requete = new URLSearchParams({ subject: `${branding.appName} — ${objet}`, body: contenu });

    // Aucun endpoint de contact n’existe encore : le message est préparé dans l’application email du visiteur.
    window.location.href = `mailto:${adresseEmail}?${requete.toString()}`;
  }

  return <main className="contact-page">
    <div className="contact-container">
      <header className="contact-heading">
        <RetourPage />
        <span className="contact-eyebrow">{<TexteLocalise phrase={"Support"} />}</span>
        <h1>{<TexteLocalise phrase={"Contactez-nous"} />}</h1>
        <p>{<TexteLocalise phrase={"Une question ? Écrivez-nous, nous vous répondrons."} />}</p>
      </header>

      <div className="contact-layout">
        <section className="contact-form-card" aria-label={traduire("Formulaire de contact")}>
          <form onSubmit={envoyer}>
            <label>{<TexteLocalise phrase={"Nom complet"} />}{' '}<span aria-hidden="true">*</span>
              <input name="nom" type="text" autoComplete="name" maxLength={120} required/>
            </label>
            <label>{<TexteLocalise phrase={"Adresse email"} />}{' '}<span aria-hidden="true">*</span>
              <input name="email" type="email" autoComplete="email" maxLength={254} required/>
            </label>
            <label>{<TexteLocalise phrase={"Objet"} />}<input name="objet" type="text" maxLength={160}/>
            </label>
            <label>{<TexteLocalise phrase={"Votre message"} />}{' '}<span aria-hidden="true">*</span>
              <textarea name="message" rows="6" maxLength={5000} required/>
            </label>
            {erreur && <p className="contact-error" role="alert">{erreur}</p>}
            <button className="contact-submit" type="submit" disabled={!adresseEmail}>
              <span aria-hidden="true">➤</span>{' '}{<TexteLocalise phrase={"Envoyer le message"} />}</button>
            <p className="contact-form-note">{<TexteLocalise phrase={"Votre application de messagerie s’ouvrira avec le message prêt à envoyer."} />}</p>
          </form>
        </section>

        <aside className="contact-details" aria-labelledby="contact-details-title">
          <h2 id="contact-details-title">{<TexteLocalise phrase={"Nos coordonnées"} />}</h2>
          {adresseEmail && <a className="contact-detail" href={`mailto:${adresseEmail}`}>
            <span className="contact-detail-icon"><IconeContact type="email"/></span>
            <span><small>{<TexteLocalise phrase={"Email"} />}</small><strong>{adresseEmail}</strong></span>
          </a>}
          {whatsapp && <a className="contact-detail" href={whatsapp} target="_blank" rel="noreferrer">
            <span className="contact-detail-icon"><IconeContact type="whatsapp"/></span>
            <span><small>{<TexteLocalise phrase={"WhatsApp"} />}</small><strong>{numeroWhatsApp ? `+${numeroWhatsApp}` : "Écrire sur WhatsApp"}</strong></span>
          </a>}
          {branding.contact.address && <div className="contact-detail">
            <span className="contact-detail-icon"><IconeContact type="adresse"/></span>
            <span><small>{<TexteLocalise phrase={"Adresse"} />}</small><strong>{branding.contact.address}</strong></span>
          </div>}
          <p className="contact-details-note">{<TexteLocalise phrase={"Vous pouvez aussi nous écrire directement par email ou WhatsApp."} />}</p>
        </aside>
      </div>
    </div>
  </main>;
}
