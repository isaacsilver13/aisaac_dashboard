import type { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  height?: number | string;
}

export function Skeleton({ height = 160, className = "", style, ...props }: SkeletonProps) {
  return (
    <div
      className={`ui-skeleton ${className}`.trim()}
      style={{ height, ...style }}
      aria-hidden="true"
      {...props}
    />
  );
}
