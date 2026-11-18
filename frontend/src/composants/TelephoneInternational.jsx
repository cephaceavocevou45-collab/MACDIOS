import { useEffect, useMemo, useRef, useState } from "react";
import { getCountries, getCountryCallingCode, isValidPhoneNumber, parsePhoneNumberFromString } from "libphonenumber-js/min";
import { TexteLocalise, traduire } from "../contexte/LangueContext";

function construirePays(langue) {
  const nomsPays = new Intl.DisplayNames([langue], { type: "region" });
  const nomsInternationaux = new Intl.DisplayNames(["en"], { type: "region" });
  return getCountries().map((code) => ({
    code,
    nom: nomsPays.of(code) || code,
    nomInternational: nomsInternationaux.of(code) || code,
    indicatif: getCountryCallingCode(code),
  })).sort((a, b) => a.nom.localeCompare(b.nom, langue));
}

export function telephoneInternationalValide(valeur) {
  return !valeur || isValidPhoneNumber(valeur);
}

function normaliserNumeroBeninoisHistorique(valeur) {
  const ancien = valeur.match(/^\+229(?!01)(\d{8})$/);
  return ancien ? `+22901${ancien[1]}` : valeur;
}

/** Sélecteur de pays accessible, avec drapeaux SVG, recherche et indicatifs. */
export default function TelephoneInternational({
  label = "Téléphone de contact (facultatif)",
  value = "",
  onChange,
  hint = "Choisissez votre pays puis saisissez votre numéro.",
  invalid = false,
  langue = "fr",
}) {
  const [pays, setPays] = useState("BJ");
  const [national, setNational] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [recherche, setRecherche] = useState("");
  const [debutListe, setDebutListe] = useState(0);
  const conteneurRef = useRef(null);
  const champRechercheRef = useRef(null);
  const onChangeRef = useRef(onChange);
  const paysDisponibles = useMemo(() => construirePays(langue), [langue]);
  const paysSelectionne = paysDisponibles.find((item) => item.code === pays) || paysDisponibles.find((item) => item.code === "BJ");
  const paysFiltres = useMemo(() => {
    const terme = recherche.trim().toLocaleLowerCase(langue);
    if (!terme) return paysDisponibles;
    return paysDisponibles.filter((item) =>
      item.nom.toLocaleLowerCase(langue).includes(terme)
      || item.code.toLowerCase().includes(terme)
      || `+${item.indicatif}`.includes(terme),
    );
  }, [langue, paysDisponibles, recherche]);
  const paysListe = useMemo(() => !recherche && paysSelectionne
    ? [paysSelectionne, ...paysFiltres.filter((item) => item.code !== paysSelectionne.code)]
    : paysFiltres, [paysFiltres, paysSelectionne, recherche]);
  const HAUTEUR_LIGNE = 60;
  const NOMBRE_LIGNES = 10;
  const lignesVisibles = paysListe.slice(debutListe, debutListe + NOMBRE_LIGNES);

  useEffect(() => {
    // Les drapeaux sont chargés uniquement sur les écrans qui proposent un téléphone.
    import("flag-icons/css/flag-icons.min.css");
  }, []);

  useEffect(() => { onChangeRef.current = onChange; }, [onChange]);

  useEffect(() => {
    if (!value) {
      setNational("");
      return;
    }
    const normalise = normaliserNumeroBeninoisHistorique(value);
    if (normalise !== value) onChangeRef.current(normalise);
    const numero = parsePhoneNumberFromString(normalise);
    if (numero) {
      if (numero.country) setPays(numero.country);
      setNational(numero.nationalNumber);
    }
  }, [value]);

  useEffect(() => {
    if (!ouvert) return undefined;
    champRechercheRef.current?.focus();
    function fermerAuClicExterieur(event) {
      if (!conteneurRef.current?.contains(event.target)) setOuvert(false);
    }
    function fermerEchap(event) {
      if (event.key === "Escape") setOuvert(false);
    }
    document.addEventListener("mousedown", fermerAuClicExterieur);
    document.addEventListener("keydown", fermerEchap);
    return () => {
      document.removeEventListener("mousedown", fermerAuClicExterieur);
      document.removeEventListener("keydown", fermerEchap);
    };
  }, [ouvert]);

  function choisirPays(item) {
    setPays(item.code);
    setOuvert(false);
    setRecherche("");
    setDebutListe(0);
    onChangeRef.current(national ? normaliserNumeroBeninoisHistorique(`+${item.indicatif}${national}`) : "");
  }

  function changerNumero(event) {
    const chiffres = event.target.value.replace(/\D/g, "");
    setNational(chiffres);
    onChangeRef.current(chiffres ? normaliserNumeroBeninoisHistorique(`+${paysSelectionne.indicatif}${chiffres}`) : "");
  }

  function changerRecherche(event) {
    setRecherche(event.target.value);
    setDebutListe(0);
  }

  return <fieldset className="international-phone">
    <legend>{traduire(label, langue)}</legend>
    <div className="international-phone-fields">
      <div className="international-phone-country" ref={conteneurRef}>
        <span className="international-phone-label">{<TexteLocalise phrase={"Pays"} />}</span>
        <button
          className="country-picker-trigger"
          type="button"
          aria-haspopup="listbox"
          aria-expanded={ouvert}
          aria-label={traduire("Pays sélectionné : {pays}, indicatif +{indicatif}", langue).replace("{pays}", paysSelectionne?.nom || "").replace("{indicatif}", paysSelectionne?.indicatif || "")}
          onClick={() => { setOuvert((actuel) => !actuel); setRecherche(""); setDebutListe(0); }}
        >
          <span className={`fi fi-${paysSelectionne?.code.toLowerCase()}`} aria-hidden="true" />
          <span className="country-picker-name">{paysSelectionne?.nom}</span>
          <span className="country-picker-code">+{paysSelectionne?.indicatif}</span>
          <span aria-hidden="true" className="country-picker-caret">⌄</span>
        </button>
        {ouvert && <div className="country-picker-menu">
          <label className="country-picker-search-wrap">
            <span className="sr-only">{<TexteLocalise phrase={"Rechercher un pays ou un indicatif"} />}</span>
            <input
              ref={champRechercheRef}
              className="country-picker-search"
              type="search"
              value={recherche}
              onChange={changerRecherche}
              placeholder={traduire("Rechercher un pays ou un indicatif")}
              autoComplete="off"
            />
          </label>
          <div
            className="country-picker-list"
            role="listbox"
            aria-label={traduire("Pays et indicatifs téléphoniques")}
            onScroll={(event) => setDebutListe(Math.max(0, Math.min(
              paysListe.length - NOMBRE_LIGNES,
              Math.floor(event.currentTarget.scrollTop / HAUTEUR_LIGNE),
            )))}
          >
            {paysListe.length === 0 ? <p className="country-picker-empty">{<TexteLocalise phrase={"Aucun pays trouvé."} />}</p> : <>
              <div style={{ height: debutListe * HAUTEUR_LIGNE }} aria-hidden="true" />
              {lignesVisibles.map((item) => <button
                key={item.code}
                type="button"
                role="option"
                aria-selected={item.code === pays}
                className={`country-picker-option ${item.code === pays ? "is-selected" : ""}`}
                onClick={() => choisirPays(item)}
              >
                <span className={`fi fi-${item.code.toLowerCase()}`} aria-hidden="true" />
                <span className="country-picker-option-name">{item.nom}<small>{item.nomInternational}</small></span>
                <span className="country-picker-option-code">+{item.indicatif}</span>
                {item.code === pays && <span className="country-picker-check" aria-hidden="true">✓</span>}
              </button>)}
              <div style={{ height: Math.max(0, paysListe.length - debutListe - lignesVisibles.length) * HAUTEUR_LIGNE }} aria-hidden="true" />
            </>}
          </div>
        </div>}
      </div>
      <label className="international-phone-number">
        <span className="international-phone-label">{<TexteLocalise phrase={"Numéro de téléphone"} />}</span>
        <span className="international-phone-entry">
          <span className="international-phone-prefix" aria-hidden="true">+{paysSelectionne?.indicatif}</span>
          <input
            type="tel"
            inputMode="tel"
            autoComplete="tel-national"
            value={national}
            onChange={changerNumero}
            placeholder={traduire("Numéro sans l’indicatif")}
            aria-invalid={invalid}
          />
        </span>
      </label>
    </div>
    <small className={invalid ? "international-phone-hint is-invalid" : "international-phone-hint"}>
      {invalid ? traduire("Ce numéro ne semble pas valide pour le pays choisi.", langue) : traduire(hint, langue)}
    </small>
  </fieldset>;
}
