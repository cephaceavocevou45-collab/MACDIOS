import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { branding } from "../config/branding";
import { api } from "../api";
import Icon from "../composants/Icon";
import { useAuth } from "../contexte/AuthContext";
import FooterApplication from "../composants/FooterApplication";
import { extraireListe, formaterFCFA } from "../utils";

const produitsLigneUne = [
  ["🍚", "Épicerie", "Riz"], ["🥜", "Épicerie", "Arachides"], ["🍅", "Produits frais", "Tomates"],
  ["🍌", "Produits frais", "Fruits"], ["🥤", "Boissons", "Jus"], ["💧", "Boissons", "Eau"],
  ["🧼", "Cosmétique", "Savon"], ["🧴", "Cosmétique", "Soin"],
];
const produitsLigneDeux = [
  ["🛢️", "Épicerie", "Huile"], ["🌶️", "Épicerie", "Épices"], ["🥬", "Produits frais", "Légumes"],
  ["🐟", "Produits frais", "Poisson"], ["📱", "Électronique", "Téléphones"], ["🔌", "Électronique", "Accessoires"],
  ["👕", "Textile", "Vêtements"], ["🧵", "Textile", "Tissus"],
];

const fonctionnalites = [
  { icone: "cart", titre: "Enregistrez vos ventes", texte: "Saisissez une vente en quelques secondes. Le stock se met à jour automatiquement." },
  { icone: "box", titre: "Suivez votre stock", texte: "Voyez ce qu’il vous reste et repérez rapidement les produits à renouveler." },
  { icone: "wallet", titre: "Gardez vos dettes en vue", texte: "Retrouvez le solde de chaque client et notez les remboursements reçus." },
  { icone: "chart", titre: "Comprenez vos journées", texte: "Un tableau de bord clair résume vos ventes et les points à surveiller." },
];

const questions = [
  ["À qui s’adresse Nobi ?", "Nobi est conçu pour les petits commerces qui veulent suivre simplement leurs ventes, leur stock et les crédits accordés aux clients."],
  ["Ai-je besoin d’un ordinateur ?", "Non. L’interface fonctionne sur téléphone Android et s’adapte aussi aux écrans d’ordinateur."],
  ["Comment le stock est-il mis à jour ?", "À chaque vente enregistrée, la quantité vendue est automatiquement retirée du stock."],
  ["Puis-je suivre les paiements de mes clients ?", "Oui. Vous pouvez enregistrer un paiement et retrouver le solde calculé à partir des dettes et paiements du client."],
];

function Marque({ clair = false }) {
  return <span className={`brand-lockup ${clair ? "brand-light" : ""}`}><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</span>;
}

function ApercuApplication() {
  return (
    <div className="hero-visual" aria-label="Aperçu illustratif du tableau de bord Nobi">
      <div className="app-preview">
        <div className="preview-top"><span className="preview-brand"><span className="brand-mark">{branding.logoMark}</span>{branding.appName}</span><span className="preview-user" /></div>
        <div className="preview-content">
          <span className="preview-demo-label">Aperçu illustratif · données fictives</span>
          <p className="preview-welcome">Bonjour, votre commerce 👋</p>
          <div className="preview-stat-grid">
            <div className="preview-stat"><small>Exemple · ventes du jour</small><strong>48 500 F</strong></div>
            <div className="preview-stat"><small>Exemple · semaine</small><strong>215 000 F</strong></div>
            <div className="preview-stat"><small>Exemple · dettes</small><strong>32 000 F</strong></div>
          </div>
          <div className="preview-chart"><div className="preview-chart-head"><span>Activité de la semaine</span><span>Exemple</span></div>
            <svg viewBox="0 0 430 130" role="img" aria-label="Graphique illustratif, données fictives">
              <path d="M10 103H420M10 68H420M10 33H420" stroke="#edf1ed" strokeWidth="1" />
              <path d="M22 92 C65 86 67 53 115 63 S177 83 210 50 S270 66 306 37 S365 50 407 19" fill="none" stroke="#17324D" strokeWidth="4" strokeLinecap="round" />
              <path d="M22 92 C65 86 67 53 115 63 S177 83 210 50 S270 66 306 37 S365 50 407 19 L407 112 L22 112Z" fill="url(#public-area)" opacity=".45" />
              <defs><linearGradient id="public-area" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#9EB5C9" /><stop offset="1" stopColor="#fff" /></linearGradient></defs>
              <circle cx="407" cy="19" r="5" fill="#D59A35" stroke="white" strokeWidth="3" />
            </svg>
          </div>
          <div className="preview-stock"><span className="preview-stock-icon"><Icon name="box" size={15} /></span><span><strong>Exemple · stock à surveiller</strong><br />Tomates · 3 unités restantes</span></div>
        </div>
      </div>
      <div className="floating-chip top"><i className="chip-dot" /> Exemple de vente <strong>+8 500 F</strong></div>
      <div className="floating-chip bottom"><span>📦</span> Exemple · stock actualisé automatiquement</div>
    </div>
  );
}

function BandeauProduits({ produits, direction, nom }) {
  return (
    <div className={`category-lane category-lane-${direction}`} aria-label={nom}>
      <div className="category-track">
        {[0, 1].map((copie) => (
          <div className="category-group" key={copie} aria-hidden={copie === 1}>
            {produits.map(([icone, categorie, nomProduit]) => (
              <div className="category-card" key={`${copie}-${nomProduit}`}>
                <span className="category-emoji" aria-hidden="true">{icone}</span>
                <span><small>{categorie}</small><strong>{nomProduit}</strong></span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AccueilPublique() {
  const { connecte } = useAuth();
  const [menuOuvert, setMenuOuvert] = useState(false);
  const [offreEssai, setOffreEssai] = useState(null);
  const [planMensuel, setPlanMensuel] = useState(null);
  const [tarifCharge, setTarifCharge] = useState(false);

  useEffect(() => {
    api.get("/api/offre-essai/").then(({ data }) => setOffreEssai(data)).catch(() => setOffreEssai(null));
    api.get("/api/plans/").then(({ data }) => {
      setPlanMensuel(extraireListe(data).find((plan) => Number(plan.duree_jours) === 30) || null);
    }).catch(() => setPlanMensuel(null)).finally(() => setTarifCharge(true));
  }, []);

  useEffect(() => {
    const page = document.querySelector(".public-page");
    const sections = page?.querySelectorAll("[data-reveal]");
    if (!page || !sections?.length || !("IntersectionObserver" in window)) return undefined;

    const observateur = new IntersectionObserver((entrees) => {
      entrees.forEach((entree) => {
        if (entree.isIntersecting) {
          entree.target.classList.add("is-visible");
          observateur.unobserve(entree.target);
        }
      });
    }, { threshold: 0.12 });

    sections.forEach((section) => observateur.observe(section));
    page.classList.add("reveal-ready");
    return () => observateur.disconnect();
  }, []);

  if (connecte) return <Navigate to="/tableau-de-bord" replace />;

  const texteCreationCompte = offreEssai?.actif ? "Créer mon compte gratuitement" : "Créer mon compte";

  const paletteStyle = {
    "--public-primary": branding.palette.primary,
    "--public-primary-dark": branding.palette.primaryDark,
    "--public-accent": branding.palette.accent,
    "--public-background": branding.palette.background,
    "--public-ink": branding.palette.ink,
    "--public-muted": branding.palette.muted,
    "--public-soft": branding.palette.soft,
    "--public-line": branding.palette.line,
  };

  return (
    <div className="public-page" style={paletteStyle}>
      <header className="public-header">
        <div className="public-container public-header-inner">
          <a href="#accueil" aria-label={`${branding.appName}, accueil`}><Marque /></a>
          <nav className={`public-links ${menuOuvert ? "is-open" : ""}`} aria-label="Navigation du site">
            <a href="#fonctionnalites" onClick={() => setMenuOuvert(false)}>Fonctionnalités</a>
            <a href="#comment-ca-marche" onClick={() => setMenuOuvert(false)}>Comment ça marche</a>
            <a href="#tarifs" onClick={() => setMenuOuvert(false)}>Tarifs</a>
            <a href="#contact" onClick={() => setMenuOuvert(false)}>Contact</a>
            <Link className="mobile-auth-link" to="/connexion" onClick={() => setMenuOuvert(false)}>Se connecter</Link>
            <Link className="mobile-auth-link" to="/inscription" onClick={() => setMenuOuvert(false)}>Créer mon compte</Link>
          </nav>
          <div className="public-actions"><Link className="btn-ghost" to="/connexion">Se connecter</Link><Link className="btn-primary btn-small" to="/inscription">Créer mon compte <Icon name="arrow" size={16} /></Link>
            <button className="mobile-menu-button" onClick={() => setMenuOuvert(!menuOuvert)} aria-label={menuOuvert ? "Fermer le menu" : "Ouvrir le menu"} aria-expanded={menuOuvert}><Icon name={menuOuvert ? "close" : "menu"} /></button>
          </div>
        </div>
      </header>

      <main id="accueil">
        <section className="hero-section" data-reveal><div className="public-container hero-grid">
            <div className="hero-copy"><span className="eyebrow"><Icon name="spark" size={15} /> Le commerce, plus facile au quotidien</span>
            <h1>Votre boutique avance. <em>Vous gardez le cap.</em></h1>
            <p>Ventes, stock et crédits clients réunis dans un outil simple, pensé pour les commerçants et accessible depuis votre téléphone.</p>
            <div className="hero-buttons"><Link to="/inscription" className="btn-primary">{texteCreationCompte} <Icon name="arrow" size={17} /></Link><a href="#fonctionnalites" className="btn-secondary">Découvrir l’application</a></div>
            <div className="trust-row"><span className="avatar-stack"><i>AM</i><i>KB</i><i>FD</i></span><span>Un outil conçu pour le quotidien des commerçants</span></div>
          </div>
          <ApercuApplication />
        </div></section>

        <section className="category-showcase" aria-label="Exemples de catégories de produits">
          <div className="category-intro"><span className="eyebrow">Pour tous les rayons</span><p>Retrouvez facilement vos produits, du marché à la boutique.</p></div>
          <BandeauProduits produits={produitsLigneUne} direction="left" nom="Épicerie et produits frais" />
          <BandeauProduits produits={produitsLigneDeux} direction="right" nom="Boissons, cosmétique, électronique et textile" />
        </section>

        <section className="public-section trust-section" data-reveal aria-labelledby="confiance-titre"><div className="public-container">
          <div className="trust-panel">
            <div className="trust-heading"><span className="eyebrow">Une offre claire</span><h2 id="confiance-titre">Pensé pour le quotidien des petits commerces</h2><p>Les outils essentiels sont réunis dans le même espace{offreEssai?.actif ? `, avec un essai gratuit de ${offreEssai.duree_jours} jours.` : "."}</p></div>
            <div className="trust-metrics">{offreEssai?.actif && <article><strong>{offreEssai.duree_jours} jours</strong><span>d’essai gratuit à l’inscription</span></article>}<article><strong>Ventes · Stock · Dettes</strong><span>les opérations clés de votre boutique</span></article><article><strong>Mobile-first</strong><span>une interface adaptée au téléphone</span></article></div>
          </div>
        </div></section>
        <section className="public-section" id="fonctionnalites" data-reveal><div className="public-container">
          <div className="section-heading"><span className="eyebrow">Tout au même endroit</span><h2>Les essentiels de votre commerce, sans complication</h2><p>Un écran clair pour suivre ce qui compte et prendre de meilleures décisions au quotidien.</p></div>
          <div className="feature-grid">{fonctionnalites.map((f) => <article className="feature-card" key={f.titre}><span className="feature-icon"><Icon name={f.icone} size={23} /></span><h3>{f.titre}</h3><p>{f.texte}</p></article>)}</div>
        </div></section>

        <section className="public-section how-section" id="comment-ca-marche" data-reveal><div className="public-container">
          <div className="section-heading"><span className="eyebrow">Pour commencer</span><h2>Prêt en trois étapes</h2><p>Pas besoin d’être expert en informatique. Commencez simplement, à votre rythme.</p></div>
          <div className="steps-grid">{[["01", "Créez votre espace", "Inscrivez votre boutique avec votre adresse email."], ["02", "Ajoutez vos produits", "Renseignez les articles et les quantités de votre stock."], ["03", "Suivez votre activité", "Notez les ventes, les crédits et les paiements depuis votre téléphone."]].map(([n, t, d]) => <article className="step-card" key={n}><span className="step-number">{n}</span><h3>{t}</h3><p>{d}</p></article>)}</div>
        </div></section>

        <section className="public-section" id="tarifs" data-reveal><div className="public-container">
          <div className="section-heading"><span className="eyebrow">Un tarif simple</span><h2>Une offre claire pour votre boutique</h2><p>Tout ce qu’il faut pour commencer à mieux gérer votre activité.</p></div>
          <article className="price-card"><div><h3>{planMensuel?.nom || "Offre commerçant"}</h3><p>Les outils essentiels pour gérer votre commerce au quotidien, réunis dans un seul espace.</p><div className="price-value" aria-live="polite">{planMensuel ? <>{formaterFCFA(planMensuel.prix)}<small> / 30 jours</small></> : tarifCharge ? "Tarif temporairement indisponible" : "Chargement du tarif…"}</div><ul className="price-list"><li><Icon name="check" size={16} /> Suivi des ventes et du stock</li><li><Icon name="check" size={16} /> Gestion des clients et des dettes</li><li><Icon name="check" size={16} /> Tableau de bord récapitulatif</li></ul></div><div className="price-side"><p>Votre activité, mieux organisée dès aujourd’hui.</p><Link to="/inscription" className="btn-primary">Créer mon compte <Icon name="arrow" size={16} /></Link>{offreEssai?.actif && <small className="price-note">Essai gratuit pendant {offreEssai.duree_jours} jours après l’inscription.</small>}</div></article>
        </div></section>

        <section className="public-section" id="faq" data-reveal><div className="public-container"><div className="section-heading"><span className="eyebrow">FAQ</span><h2>Vos questions, simplement</h2></div><div className="faq-list">{questions.map(([question, reponse]) => <details className="faq-item" key={question}><summary>{question}</summary><p>{reponse}</p></details>)}</div></div></section>

        <section className="public-section bottom-cta-section" data-reveal><div className="public-container"><div className="cta-panel"><span className="eyebrow">À vous de jouer</span><h2>Faites de la place pour l’essentiel.</h2><p>Commencez à suivre votre commerce avec un outil simple et adapté à votre quotidien.</p><Link to="/inscription" className="btn-primary">{texteCreationCompte} <Icon name="arrow" size={16} /></Link></div></div></section>
      </main>
      <FooterApplication />
    </div>
  );
}
