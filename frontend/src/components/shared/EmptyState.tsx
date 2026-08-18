import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  iconClassName?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon: Icon, title, description, iconClassName, action }) => {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon size={22} className={iconClassName} />
      </div>
      <div className="empty-title">{title}</div>
      <div className="empty-description">{description}</div>
      {action && (
        <button className="btn btn-primary" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
};
