import type { HTMLAttributes, ReactNode } from "react";

interface StatProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: ReactNode;
}

export function Stat({ label, value, className = "", ...props }: StatProps) {
  return (
    <div className={`ui-stat ${className}`.trim()} {...props}>
      <span className="ui-stat-label">{label}</span>
      <span className="ui-stat-value">{value}</span>
    </div>
  );
}
