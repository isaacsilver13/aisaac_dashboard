import type { HTMLAttributes, ReactNode } from "react";

export type CardVariant = "default" | "elevated" | "interactive" | "subtle";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
}

const variantClass: Record<CardVariant, string> = {
  default: "",
  elevated: "ui-card-elevated",
  interactive: "ui-card-interactive",
  subtle: "ui-card-subtle",
};

export function Card({ variant = "default", className = "", children, ...props }: CardProps) {
  const classes = ["ui-card", variantClass[variant], className].filter(Boolean).join(" ");
  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`ui-card-header ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardContent({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`ui-card-footer ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}
