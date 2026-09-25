import type { HTMLAttributes, ReactNode } from "react";

import type { Tone } from "./tone";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  children: ReactNode;
}

export function Badge({ tone = "neutral", className = "", children, ...props }: BadgeProps) {
  return (
    <span className={`ui-badge ui-badge-${tone} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}
