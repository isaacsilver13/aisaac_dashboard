import type { ReactNode } from "react";
import { Archive } from "iconoir-react";

interface EmptyStateProps {
  message: string;
  icon?: ReactNode;
}

export function EmptyState({ message, icon }: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      {icon ?? <Archive width={18} height={18} aria-hidden="true" />}
      <span>{message}</span>
    </div>
  );
}
