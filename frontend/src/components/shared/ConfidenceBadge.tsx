import React from 'react';

interface ConfidenceBadgeProps {
  confidence: number; // 0–1 scale (e.g. 0.996)
}

function getConfidenceBand(confidence: number): { label: string; className: string } {
  const pct = confidence * 100;
  if (pct >= 98) return { label: 'High', className: 'high' };
  if (pct >= 90) return { label: 'Medium', className: 'medium' };
  return { label: 'Low', className: 'low' };
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence }) => {
  const { label, className } = getConfidenceBand(confidence);
  const pct = Math.round(confidence * 100);

  return (
    <span className={`confidence-badge ${className}`} title={`${label} confidence: ${pct}%`}>
      <span className={`confidence-dot ${className}`} />
      <span>{pct}%</span>
    </span>
  );
};
