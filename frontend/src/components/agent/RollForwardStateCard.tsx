import React, { useState } from 'react';
import { ShieldAlert, ListChecks, CircleCheck, CircleX, Loader2, PlayCircle } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import type { RollForwardAssessment } from '../../api/agent';

// What the Agent shows for a roll-forward request. Every value here comes from
// the server's deterministic assessment — inputs, periods, blockers, plan counts
// — so the card states facts rather than a model's account of them.
//
// It has exactly three faces, and none of them can claim a completed run: a
// completed roll-forward is rendered by RollForwardResultCard, which only exists
// when a real execution report does.

const STAGE_TITLE: Record<RollForwardAssessment['stage'], string> = {
  BLOCKED: 'Roll-Forward — Not ready',
  PLAN_UNAVAILABLE: 'Roll-Forward — Not ready',
  PLAN_READY: 'Roll-Forward Plan',
  EXECUTED: 'Roll-Forward',
};

export const RollForwardStateCard: React.FC<{
  assessment: RollForwardAssessment;
  messageId: string;
}> = ({ assessment, messageId }) => {
  const approveRollForwardPlan = useAgentStore((s) => s.approveRollForwardPlan);
  const [approving, setApproving] = useState(false);
  const [approver, setApprover] = useState('');
  const [showApprover, setShowApprover] = useState(false);

  const planReady = assessment.stage === 'PLAN_READY' && assessment.plan;
  const period = assessment.periods?.historical_period && assessment.periods?.current_period
    ? `${assessment.periods.historical_period} → ${assessment.periods.current_period}`
    : null;

  const runApproval = async () => {
    if (!approver.trim()) return;
    setApproving(true);
    try {
      await approveRollForwardPlan(messageId, approver.trim());
    } finally {
      setApproving(false);
      setShowApprover(false);
    }
  };

  return (
    <div
      data-testid="roll-forward-state"
      data-stage={assessment.stage}
      style={{
        marginTop: 'var(--space-2)',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${planReady ? 'var(--accent)' : 'var(--warning)'}`,
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        {planReady
          ? <ListChecks size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          : <ShieldAlert size={14} style={{ color: 'var(--warning)', flexShrink: 0 }} />}
        <span style={{ flex: 1, fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
          {STAGE_TITLE[assessment.stage]}
        </span>
        {period && (
          <span data-testid="roll-forward-periods" style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
            {period}
          </span>
        )}
      </div>

      {planReady ? (
        <>
          <div style={{
            display: 'flex', gap: 'var(--space-4)', padding: 'var(--space-2) 0',
            borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)',
            marginBottom: 'var(--space-2)',
          }}>
            <Stat label="tables to update" value={assessment.plan!.tables_to_update} testId="rf-plan-tables" />
            <Stat label="cells to update" value={assessment.plan!.cells_to_update} testId="rf-plan-cells" />
            <Stat label="rows to insert" value={assessment.plan!.rows_to_insert} testId="rf-plan-rows" />
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>
            Nothing has been changed yet. Execution requires your explicit approval.
          </div>

          {showApprover ? (
            <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
              <input
                data-testid="rf-approver-input"
                value={approver}
                onChange={(e) => setApprover(e.target.value)}
                placeholder="Your name or email"
                style={{
                  flex: 1, fontSize: 'var(--text-xxs)', padding: '4px 6px',
                  border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                }}
              />
              <button
                className="btn btn-primary btn-sm"
                data-testid="rf-confirm-approve"
                onClick={runApproval}
                disabled={approving || !approver.trim()}
                style={{ fontSize: 'var(--text-xxs)' }}
              >
                {approving ? <Loader2 size={11} className="animate-spin" /> : <PlayCircle size={11} />}
                {approving ? 'Executing…' : 'Approve & Execute'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
              <button className="btn btn-secondary btn-sm" data-testid="rf-review-plan"
                      style={{ fontSize: 'var(--text-xxs)' }}>
                Review Plan
              </button>
              <button className="btn btn-primary btn-sm" data-testid="rf-approve-execute"
                      onClick={() => setShowApprover(true)} style={{ fontSize: 'var(--text-xxs)' }}>
                Approve &amp; Execute
              </button>
            </div>
          )}
        </>
      ) : (
        <>
          {assessment.satisfied_inputs.length > 0 && (
            <div style={{ marginBottom: 'var(--space-2)' }}>
              <Label>Required</Label>
              {assessment.satisfied_inputs.map((name) => (
                <Row key={name} ok testId={`rf-input-${name.replace(/\s+/g, '-')}`}>{name}</Row>
              ))}
            </div>
          )}

          <Label>Blocked</Label>
          <div data-testid="rf-blockers">
            {assessment.blockers.map((blocker) => (
              <Row key={`${blocker.code}-${blocker.subject}`} ok={false}
                   testId={`rf-blocker-${blocker.code}`} title={blocker.detail}>
                {blocker.subject}
              </Row>
            ))}
          </div>

          <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: 'var(--space-2)' }}>
            No document has been modified and no output has been produced.
          </div>
        </>
      )}
    </div>
  );
};

const Label: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    fontSize: '10px', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
    color: 'var(--text-tertiary)', marginBottom: 2,
  }}>{children}</div>
);

const Row: React.FC<{ ok: boolean; children: React.ReactNode; testId: string; title?: string }> = ({
  ok, children, testId, title,
}) => (
  <div data-testid={testId} title={title} style={{
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-xxs)',
    color: ok ? 'var(--text-secondary)' : 'var(--error)', padding: '1px 0',
  }}>
    {ok ? <CircleCheck size={11} style={{ color: 'var(--success)' }} />
        : <CircleX size={11} style={{ color: 'var(--error)' }} />}
    <span>{children}</span>
  </div>
);

const Stat: React.FC<{ label: string; value: number; testId: string }> = ({ label, value, testId }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
    <span data-testid={testId} style={{
      fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2,
    }}>{value.toLocaleString()}</span>
    <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{label}</span>
  </div>
);
