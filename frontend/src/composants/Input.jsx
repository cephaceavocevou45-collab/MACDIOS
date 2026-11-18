import { traduire, useLangue } from "../contexte/LangueContext";

export default function Input({ label, hint, className = "", as = "input", ...props }) {
  const { langue } = useLangue();
  const Tag = as;
  return (
    <label className={`field-wrap ${className}`}>
      {label && <span className="field-label">{traduire(label, langue)}</span>}
      <Tag className="field-control" {...props} />
      {hint && <span className="field-hint">{traduire(hint, langue)}</span>}
    </label>
  );
}
