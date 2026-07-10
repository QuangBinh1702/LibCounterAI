interface SkeletonRowsProps {
  rows?: number;
}

export function SkeletonRows({ rows = 5 }: SkeletonRowsProps) {
  const count = Math.max(1, rows)
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton-row" />
      ))}
    </div>
  );
}
