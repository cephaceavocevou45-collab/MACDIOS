import { useEffect, useRef, useState } from "react";
import Button from "./Button";
import Icon from "./Icon";
import Modal from "./Modal";
import { TexteLocalise } from "../contexte/LangueContext";

const FORMATS_SCANNABLES = ["qr_code", "ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "itf", "codabar", "data_matrix", "pdf417", "aztec"];

export default function ScannerCodeProduit({ onDetecte }) {
  const [ouvert, setOuvert] = useState(false);
  const [erreur, setErreur] = useState("");
  const videoRef = useRef(null);
  const fluxRef = useRef(null);
  const onDetecteRef = useRef(onDetecte);

  useEffect(() => { onDetecteRef.current = onDetecte; }, [onDetecte]);

  useEffect(() => {
    if (!ouvert) return undefined;
    let actif = true;
    let animation = 0;
    const arreterFlux = () => {
      if (animation) window.cancelAnimationFrame(animation);
      fluxRef.current?.getTracks().forEach((piste) => piste.stop());
      fluxRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    };
    async function demarrer() {
      try {
        if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) throw new Error("camera");
        if (!("BarcodeDetector" in window)) throw new Error("unsupported");
        const formatsDisponibles = await window.BarcodeDetector.getSupportedFormats();
        const formats = FORMATS_SCANNABLES.filter((format) => formatsDisponibles.includes(format));
        if (!formats.length) throw new Error("unsupported");
        const detecteur = new window.BarcodeDetector({ formats });
        const flux = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        if (!actif) { flux.getTracks().forEach((piste) => piste.stop()); return; }
        fluxRef.current = flux;
        videoRef.current.srcObject = flux;
        await videoRef.current.play();
        const lireImage = async () => {
          if (!actif || !videoRef.current) return;
          try {
            if (videoRef.current.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
              const resultats = await detecteur.detect(videoRef.current);
              const code = resultats.find((resultat) => resultat.rawValue?.trim());
              if (code) {
                if (code.rawValue.trim().length > 64) setErreur("Le contenu scanné dépasse la longueur autorisée pour un code produit.");
                else { onDetecteRef.current(code.rawValue.trim()); setOuvert(false); }
              }
            }
          } catch { /* Une image momentanément illisible sera réessayée à la prochaine frame. */ }
          if (actif) animation = window.requestAnimationFrame(lireImage);
        };
        lireImage();
      } catch (cause) {
        if (!actif) return;
        setErreur(cause.message === "unsupported"
          ? "Le scan caméra n’est pas pris en charge par ce navigateur. Saisissez le code manuellement."
          : "Impossible d’accéder à la caméra. Autorisez son utilisation ou saisissez le code manuellement.");
      }
    }
    demarrer();
    return () => { actif = false; arreterFlux(); };
  }, [ouvert]);

  function ouvrir() { setErreur(""); setOuvert(true); }

  return <>
    <Button type="button" variant="secondary" className="barcode-scan-button" onClick={ouvrir} aria-label="Scanner le code du produit"><Icon name="scan" size={18}/><span><TexteLocalise phrase="Scanner code-barres / QR"/></span></Button>
    <Modal open={ouvert} title="Scanner le code du produit" onClose={() => setOuvert(false)}>
      <div className="barcode-scanner-content">
        <video ref={videoRef} className="barcode-scanner-video" muted playsInline aria-label="Aperçu caméra pour scanner un code"/>
        <p><TexteLocalise phrase="Placez le code-barres ou le QR code devant la caméra."/></p>
        {erreur && <p className="barcode-scanner-error" role="status"><TexteLocalise phrase={erreur}/></p>}
      </div>
    </Modal>
  </>;
}
