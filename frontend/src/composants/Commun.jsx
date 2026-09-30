export function Chargement({ texte = "Chargement…" }) {
  return <p className="py-8 text-center text-lg text-gray-600" role="status">{texte}</p>;
}

export function Erreur({ texte }) {
  return texte ? <p className="rounded-xl bg-red-50 p-4 font-medium text-red-800" role="alert">{texte}</p> : null;
}

export function Succes({ texte }) {
  return texte ? <p className="rounded-xl bg-green-50 p-4 font-medium text-green-800" role="status">{texte}</p> : null;
}

export function Champ({ label, className = "", ...props }) {
  return (
    <label className={`block space-y-2 ${className}`}>
      <span className="font-semibold text-gray-800">{label}</span>
      <input className="champ" {...props} />
    </label>
  );
}
