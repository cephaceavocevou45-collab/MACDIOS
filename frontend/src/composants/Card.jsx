export default function Card({ className = "", children, ...props }) {
  return <section className={`surface-card ${className}`} {...props}>{children}</section>;
}
