import type { HTMLAttributes } from "react";

import type { Tone } from "./tone";

interface StatusDotProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  /** Accessible label — status must never be conveyed by color alone. */
  label: string;
}

export function StatusDot({ tone = "neutral", label, className = "", ...props }: StatusDotProps) {
  return (
    <span
      className={`ui-status-dot ui-status-dot-${tone} ${className}`.trim()}
      role="img"
      aria-label={label}
      {...props}
    />
  );
}
