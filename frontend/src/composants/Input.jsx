export default function Input({ label, hint, className = "", as = "input", ...props }) {
  const Tag = as;
  return (
    <label className={`field-wrap ${className}`}>
      {label && <span className="field-label">{label}</span>}
      <Tag className="field-control" {...props} />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}
