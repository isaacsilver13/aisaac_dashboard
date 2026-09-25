import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function SectionHeader({ title, description, actions }: SectionHeaderProps) {
  return (
    <div className="ui-section-header">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {actions}
    </div>
  );
}
