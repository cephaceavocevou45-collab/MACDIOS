export default function Button({ variant = "primary", size = "normal", className = "", type = "button", children, ...props }) {
  const variantes = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    ghost: "btn-ghost",
    danger: "btn-danger",
  };
  return <button type={type} className={`${variantes[variant]} ${size === "small" ? "btn-small" : ""} ${className}`} {...props}>{children}</button>;
}
