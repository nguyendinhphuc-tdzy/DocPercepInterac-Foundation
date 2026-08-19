import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { sendPilotEvent } from '../../api/pilot';
import { usePilotStore } from '../../state/pilotStore';

interface PilotFeedbackProps {
  runId?: string | null;
}

const REASONS = [
  'Wrong target',
  'Not useful',
  'Too slow',
  "Didn't understand request",
  'Citation unclear',
];

export const PilotFeedback: React.FC<PilotFeedbackProps> = ({ runId }) => {
  const pilotSessionId = usePilotStore((s) => s.pilotSessionId);
  const [submitted, setSubmitted] = useState(false);
  const [showReasons, setShowReasons] = useState(false);

  const submit = (helpful: boolean, reason?: string) => {
    sendPilotEvent('pilot.feedback.submitted', {
      pilot_session_id: pilotSessionId,
      run_id: runId ?? undefined,
      helpful,
      reason,
    });
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
        Thanks for the feedback.
      </div>
    );
  }

  if (showReasons) {
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: 'var(--space-1)' }}>
        {REASONS.map((reason) => (
          <button
            key={reason}
            onClick={() => submit(false, reason)}
            className="btn btn-ghost btn-sm"
            style={{
              fontSize: 'var(--text-xxs)',
              padding: '2px 8px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-full)',
              color: 'var(--text-secondary)',
            }}
          >
            {reason}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: 'var(--space-1)' }}>
      <span style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)' }}>Helpful?</span>
      <button
        onClick={() => submit(true)}
        className="btn btn-ghost btn-sm"
        title="Yes, helpful"
        style={{ padding: '2px 6px', color: 'var(--text-secondary)' }}
      >
        <ThumbsUp size={12} />
      </button>
      <button
        onClick={() => setShowReasons(true)}
        className="btn btn-ghost btn-sm"
        title="Not helpful"
        style={{ padding: '2px 6px', color: 'var(--text-secondary)' }}
      >
        <ThumbsDown size={12} />
      </button>
    </div>
  );
};
