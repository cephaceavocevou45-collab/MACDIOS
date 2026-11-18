import { traduire, useLangue } from "../contexte/LangueContext";

export default function Badge({ tone = "green", children }) {
  const { langue } = useLangue();
  return <span className={`badge badge-${tone}`}>{typeof children === "string" ? traduire(children, langue) : children}</span>;
}
