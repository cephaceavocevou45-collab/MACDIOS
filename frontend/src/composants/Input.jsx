import { useState } from "react";
import { traduire, useLangue } from "../contexte/LangueContext";
import Icon from "./Icon";

export default function Input({ label, hint, className = "", as = "input", type = "text", ...props }) {
  const { langue } = useLangue();
  const [motDePasseVisible, setMotDePasseVisible] = useState(false);
  const Tag = as;
  const estMotDePasse = type === "password";
  const typeAffiche = estMotDePasse && motDePasseVisible ? "text" : type;
  const typeProps = as === "input" ? { type: typeAffiche } : {};
  return (
    <label className={`field-wrap ${className}`}>
      {label && <span className="field-label">{traduire(label, langue)}</span>}
      {estMotDePasse ? (
        <span className="password-field-wrap">
          <Tag className="field-control password-field-control" {...typeProps} {...props} />
          <button
            type="button"
            className="password-visibility-toggle"
            aria-label={traduire(motDePasseVisible ? "Masquer le mot de passe" : "Afficher le mot de passe", langue)}
            aria-pressed={motDePasseVisible}
            onClick={() => setMotDePasseVisible((visible) => !visible)}
          >
            <Icon name={motDePasseVisible ? "eyeOff" : "eye"} size={19} />
          </button>
        </span>
      ) : <Tag className="field-control" {...typeProps} {...props} />}
      {hint && <span className="field-hint">{traduire(hint, langue)}</span>}
    </label>
  );
}
