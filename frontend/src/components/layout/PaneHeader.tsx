import type { ReactNode } from 'react';

interface PaneHeaderProps {
  title: string;
  right?: ReactNode;
}

export function PaneHeader({ title, right }: PaneHeaderProps) {
  return (
    <div className="pane-header">
      <span>{title}</span>
      {right}
    </div>
  );
}
