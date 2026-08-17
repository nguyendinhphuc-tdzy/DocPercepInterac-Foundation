import React from 'react';
import { CheckCircle, AlertCircle, Loader2, Clock, AlertTriangle } from 'lucide-react';

type StatusType = 'ready' | 'processing' | 'error' | 'warning' | 'idle';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  showDot?: boolean;
}

const STATUS_CONFIG: Record<StatusType, { icon: React.ElementType; defaultLabel: string }> = {
  ready: { icon: CheckCircle, defaultLabel: 'Ready' },
  processing: { icon: Loader2, defaultLabel: 'Processing' },
  error: { icon: AlertCircle, defaultLabel: 'Error' },
  warning: { icon: AlertTriangle, defaultLabel: 'Warning' },
  idle: { icon: Clock, defaultLabel: 'Idle' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, showDot = true }) => {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const displayLabel = label ?? config.defaultLabel;

  return (
    <span className={`status-badge ${status}`} role="status" aria-label={displayLabel}>
      {showDot ? (
        <span className={`status-dot ${status}`} />
      ) : (
        <Icon size={12} className={status === 'processing' ? 'animate-spin' : ''} />
      )}
      <span>{displayLabel}</span>
    </span>
  );
};
