import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  message: string;
  icon?: ReactNode;
}

export function EmptyState({ message, icon }: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      {icon ?? <Inbox size={18} aria-hidden="true" />}
      <span>{message}</span>
    </div>
  );
}
