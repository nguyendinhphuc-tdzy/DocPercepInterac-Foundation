import React from 'react';
import { CheckCircle2, AlertTriangle, CircleDashed, Ban } from 'lucide-react';
import type { DomainReadiness, DomainStatus } from '../../api/workflow';

// Which source domains the uploaded evidence can actually support, in the
// user's vocabulary. Deliberately free of internals: no role enums, no policy
// names, no readiness codes — the server already translated those.

const STATUS_STYLE: Record<DomainStatus, { color: string; background: string; border: string }> = {
  SUPPORTED: { color: 'var(--success)', background: 'var(--success-light)', border: 'var(--success-border)' },
  HUMAN_REVIEW: { color: 'var(--warning)', background: 'var(--warning-light)', border: 'var(--warning-border)' },
  MISSING_SOURCE: { color: 'var(--text-tertiary)', background: 'var(--bg-hover)', border: 'var(--border)' },
  BLOCKED: { color: 'var(--error)', background: 'var(--error-light)', border: 'var(--error-border)' },
};

function StatusIcon({ status }: { status: DomainStatus }) {
  const style = { color: STATUS_STYLE[status].color, flexShrink: 0 };
  switch (status) {
    case 'SUPPORTED': return <CheckCircle2 size={13} style={style} />;
    case 'HUMAN_REVIEW': return <AlertTriangle size={13} style={style} />;
    case 'MISSING_SOURCE': return <CircleDashed size={13} style={style} />;
    case 'BLOCKED': return <Ban size={13} style={style} />;
  }
}

export const ReadinessSummary: React.FC<{ readiness: DomainReadiness[] }> = ({ readiness }) => (
  <div data-testid="readiness-summary" style={{ padding: 'var(--space-2)' }}>
    <div style={{
      fontSize: 'var(--text-xxs)',
      fontWeight: 600,
      color: 'var(--text-tertiary)',
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      marginBottom: 'var(--space-2)',
    }}>
      What this year's sources support
    </div>

    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {readiness.map((domain) => {
        const style = STATUS_STYLE[domain.status];
        return (
          <div
            key={domain.domain_id}
            data-testid={`readiness-row-${domain.domain_id}`}
            data-status={domain.status}
            title={domain.detail}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: '5px var(--space-2)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
            }}
          >
            <StatusIcon status={domain.status} />
            <span style={{
              flex: 1,
              minWidth: 0,
              fontSize: 'var(--text-xs)',
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {domain.display_name}
            </span>
            <span style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.02em',
              textTransform: 'uppercase',
              color: style.color,
              background: style.background,
              border: `1px solid ${style.border}`,
              borderRadius: 'var(--radius-sm)',
              padding: '1px 5px',
              whiteSpace: 'nowrap',
            }}>
              {domain.status_label}
            </span>
          </div>
        );
      })}
    </div>
  </div>
);
