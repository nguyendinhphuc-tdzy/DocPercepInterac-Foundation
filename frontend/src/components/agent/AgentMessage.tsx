import React from 'react';
import { Bot, User, CheckCircle, Loader2, Circle, ArrowRight, Check, X, MapPin } from 'lucide-react';
import { useAgentStore, type AgentMessage as AgentMessageType } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { usePilotStore } from '../../state/pilotStore';
import { sendPilotEvent } from '../../api/pilot';
import { PilotFeedback } from './PilotFeedback';
import type { Citation } from '../../api/agent';

interface AgentMessageProps {
  message: AgentMessageType;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const { confirmAction, rejectAction } = useAgentStore();
  const { documents, setActiveDocClientId } = useWorkspaceStore();
  const { setSelectedElementId } = useSyncStore();
  const pilotSessionId = usePilotStore((s) => s.pilotSessionId);

  const handleCitationClick = (citation: Citation) => {
    sendPilotEvent('agent.citation.clicked', {
      pilot_session_id: pilotSessionId,
      run_id: message.runId,
      doc_id: citation.doc_id,
      element_id: citation.element_id,
    });

    // 1. Switch active document if necessary
    const targetDoc = documents.find((d) => d.docId === citation.doc_id);
    if (targetDoc) {
      setActiveDocClientId(targetDoc.clientId);
    }

    // 2. Select element
    setSelectedElementId(citation.element_id);

    // 3. Scroll to element in DOM if visible
    setTimeout(() => {
      const el = document.querySelector(`[data-element-id="${citation.element_id}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      sendPilotEvent('agent.reveal.completed', {
        pilot_session_id: pilotSessionId,
        run_id: message.runId,
        doc_id: citation.doc_id,
        element_id: citation.element_id,
        status: el ? 'success' : 'not_found',
      });
    }, 150);
  };

  const showFeedback =
    !isUser &&
    ((message.citations && message.citations.length > 0) ||
      (message.proposedActions && message.proposedActions.length > 0) ||
      message.content.toLowerCase().startsWith('error'));

  return (
    <div className={`agent-message ${message.role} animate-fadeIn`}>
      {/* Avatar */}
      <div style={{
        width: 28,
        height: 28,
        borderRadius: 'var(--radius-full)',
        background: isUser ? 'var(--accent)' : 'var(--bg-hover)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        marginTop: 2,
      }}>
        {isUser ? (
          <User size={14} style={{ color: 'var(--text-inverse)' }} />
        ) : (
          <Bot size={14} style={{ color: 'var(--text-secondary)' }} />
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className={`agent-bubble ${message.role}`} style={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </div>

        {/* Citations / Provenance Badges */}
        {message.citations && message.citations.length > 0 && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-1)',
            marginTop: 'var(--space-2)',
          }}>
            {message.citations.map((c, i) => (
              <button
                key={i}
                onClick={() => handleCitationClick(c)}
                className="btn btn-ghost btn-sm"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-full)',
                  fontSize: 'var(--text-xxs)',
                  padding: '2px 8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  color: 'var(--accent)',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
                title={`Click to focus ${c.element_name} in ${c.doc_name ?? 'document'}`}
              >
                <MapPin size={10} />
                <span>{c.doc_name ? `${c.doc_name} · ` : ''}{c.element_name || c.type}</span>
              </button>
            ))}
          </div>
        )}

        {/* Proposed Action Cards */}
        {message.proposedActions && message.proposedActions.length > 0 && (
          <div style={{ marginTop: 'var(--space-2)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {message.proposedActions.map((action) => (
              <div
                key={action.action_id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderLeft: '3px solid var(--accent)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-2) var(--space-3)',
                  fontSize: 'var(--text-xs)',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    Governed Action Proposal
                  </span>
                  <span style={{
                    fontSize: 'var(--text-xxs)',
                    background: 'var(--bg-surface-secondary)',
                    padding: '1px 6px',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-secondary)',
                  }}>
                    {action.doc_name} · {action.element_name}
                  </span>
                </div>

                <div style={{
                  background: 'var(--bg-surface-secondary)',
                  padding: 'var(--space-2)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-2)',
                  margin: 'var(--space-1) 0',
                }}>
                  <span style={{ textDecoration: 'line-through', opacity: 0.7, color: 'var(--text-secondary)' }}>
                    {action.current_value || '(empty)'}
                  </span>
                  <ArrowRight size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>
                    {action.proposed_value}
                  </span>
                </div>

                <div style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>
                  Rationale: {action.rationale}
                </div>

                {/* Actions Button Bar */}
                {action.status === 'proposed' && (
                  <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => rejectAction(message.id, action.action_id)}
                      style={{ fontSize: 'var(--text-xs)', padding: '2px 8px' }}
                    >
                      <X size={12} style={{ marginRight: 4 }} />
                      Reject
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => confirmAction(message.id, action.action_id)}
                      style={{ fontSize: 'var(--text-xs)', padding: '2px 10px' }}
                    >
                      <Check size={12} style={{ marginRight: 4 }} />
                      Confirm & Apply
                    </button>
                  </div>
                )}

                {action.status === 'applied' && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--success, #16a34a)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                  }}>
                    <CheckCircle size={13} />
                    <span>Applied & Persisted to Document</span>
                  </div>
                )}

                {action.status === 'rejected' && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--text-tertiary)',
                    fontSize: 'var(--text-xs)',
                  }}>
                    <X size={13} />
                    <span>Proposal Rejected</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Progress Steps */}
        {message.steps && message.steps.length > 0 && (
          <div className="agent-progress" style={{ marginTop: 'var(--space-2)' }}>
            {message.steps.map((step, i) => (
              <div key={i} className={`agent-progress-step ${step.status}`}>
                {step.status === 'done' && <CheckCircle size={14} />}
                {step.status === 'active' && <Loader2 size={14} className="animate-spin" />}
                {step.status === 'pending' && <Circle size={14} />}
                <span>{step.label}</span>
              </div>
            ))}
          </div>
        )}

        {/* Pilot feedback (shown at task-completion-like moments only, not every turn) */}
        {showFeedback && <PilotFeedback runId={message.runId} />}

        {/* Timestamp */}
        <div style={{
          fontSize: 'var(--text-xxs)',
          color: 'var(--text-tertiary)',
          marginTop: 'var(--space-1)',
        }}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

