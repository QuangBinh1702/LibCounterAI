interface SkeletonRowsProps {
  rows?: number;
}

export function SkeletonRows({ rows = 5 }: SkeletonRowsProps) {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row" />
      ))}
    </div>
  );
}
