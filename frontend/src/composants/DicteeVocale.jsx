import { useEffect, useRef, useState } from "react";
import { localePourLangue, TexteLocalise, useLangue } from "../contexte/LangueContext";
import Button from "./Button";
import Icon from "./Icon";

export default function DicteeVocale({ onTranscription, aide, className = "" }) {
  const [ecouteActive, setEcouteActive] = useState(false);
  const [transcription, setTranscription] = useState("");
  const [erreur, setErreur] = useState("");
  const reconnaissanceRef = useRef(null);
  const { langue } = useLangue();

  useEffect(() => () => reconnaissanceRef.current?.abort(), []);

  function basculerEcoute() {
    if (ecouteActive) {
      reconnaissanceRef.current?.stop();
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setErreur("La dictée vocale n’est pas prise en charge par ce navigateur.");
      return;
    }
    setErreur("");
    setTranscription("");
    const reconnaissance = new SpeechRecognition();
    reconnaissance.lang = localePourLangue(langue);
    reconnaissance.continuous = true;
    reconnaissance.interimResults = true;
    reconnaissance.onstart = () => setEcouteActive(true);
    reconnaissance.onresult = (event) => {
      const phrase = Array.from(event.results).map((resultat) => resultat[0].transcript).join(" ").trim();
      setTranscription(phrase);
      const phraseConfirmee = Array.from(event.results).filter((resultat) => resultat.isFinal)
        .map((resultat) => resultat[0].transcript).join(" ").trim();
      if (phraseConfirmee) onTranscription(phraseConfirmee, { final: true });
    };
    reconnaissance.onerror = (event) => {
      if (event.error !== "aborted" && event.error !== "no-speech") setErreur("La dictée a échoué. Vérifiez l’autorisation du microphone puis réessayez.");
    };
    reconnaissance.onend = () => { setEcouteActive(false); reconnaissanceRef.current = null; };
    reconnaissanceRef.current = reconnaissance;
    try { reconnaissance.start(); }
    catch {
      reconnaissanceRef.current = null;
      setEcouteActive(false);
      setErreur("La dictée a échoué. Vérifiez l’autorisation du microphone puis réessayez.");
    }
  }

  return <div className={`voice-dictation ${className}`}>
    <Button type="button" variant={ecouteActive ? "danger" : "secondary"} onClick={basculerEcoute} aria-pressed={ecouteActive}>
      <Icon name="microphone" size={18}/>{" "}<TexteLocalise phrase={ecouteActive ? "Arrêter la dictée" : "Dicter les informations"}/>
    </Button>
    {aide && <p><TexteLocalise phrase={aide}/></p>}
    {transcription && <p className="voice-dictation-transcript" aria-live="polite"><strong><TexteLocalise phrase="Transcription"/> :</strong> {transcription}</p>}
    {ecouteActive && <p className="voice-dictation-status" aria-live="polite"><TexteLocalise phrase="Écoute en cours… Parlez maintenant."/></p>}
    {erreur && <p className="contact-error" role="status"><TexteLocalise phrase={erreur}/></p>}
  </div>;
}
