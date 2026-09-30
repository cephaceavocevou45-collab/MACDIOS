export function Skeleton({ className = "" }) {
  return <span className={`skeleton ${className}`} aria-hidden="true" />;
}

export function SkeletonCard() {
  return <div className="surface-card skeleton-card"><Skeleton className="w-1/3"/><Skeleton className="w-2/3 h-8"/><Skeleton className="w-1/2"/></div>;
}
