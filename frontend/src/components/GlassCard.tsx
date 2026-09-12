import type { CSSProperties, HTMLAttributes, ReactNode } from "react";

import { glass } from "../theme/tokens";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function GlassCard({ children, className = "", style, ...props }: GlassCardProps) {
  const glassVariables = {
    "--glass-blur": glass.blur,
    "--glass-background": glass.background,
    "--glass-border": glass.border,
    "--glass-shadow": glass.shadow,
    ...style,
  } as CSSProperties;

  return (
    <div className={`glass-card ${className}`} style={glassVariables} {...props}>
      {children}
    </div>
  );
}