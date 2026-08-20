import React, { useRef, useEffect, useState } from 'react';
import { Bot, Sparkles, FlaskConical, AlertCircle, RefreshCw, ArrowRight, X } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { usePilotStore } from '../../state/pilotStore';
import { AgentComposer } from './AgentComposer';
import { AgentMessage as AgentMessageComponent } from './AgentMessage';
import { EmptyState } from '../shared/EmptyState';
import { AGENT_MODELS, getModelLabel, type AgentModelId } from '../../api/agent';

/**
 * Headline for the provider error card, per normalized backend error_type.
 * Every variant names the failed model and only that model — the card must
 * never read as if some other model has already answered.
 */
function errorHeadline(errorType: string | undefined, modelName: string): string {
  switch (errorType) {
    case 'config_missing':
      return `${modelName} is not available in this environment`;
    case 'auth_error':
      return `${modelName} could not authenticate`;
    case 'timeout':
      return `${modelName} timed out`;
    case 'rate_limited':
      return `${modelName} has reached its quota`;
    case 'invalid_request':
      return `${modelName} rejected the request`;
    case 'malformed_response':
      return `${modelName} returned an unreadable response`;
    case 'content_blocked':
      return `${modelName} declined this request`;
    case 'unsupported_operation':
      return `${modelName} does not support this operation`;
    default:
      return `${modelName} is temporarily unavailable`;
  }
}

export const AgentPane: React.FC = () => {
  const {
    messages,
    status,
    providerError,
    retryFailedMessage,
    switchModelAndRetry,
    dismissProviderError,
  } = useAgentStore();
  const { documents } = useWorkspaceStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isSwitchListOpen, setIsSwitchListOpen] = useState(false);
  const {
    pilotModeEnabled,
    togglePilotMode,
    scenarios,
    activeScenarioId,
    taskId,
    startTask,
    completeTask,
    abandonTask,
  } = usePilotStore();

  // Auto-scroll to bottom on new messages or error card appearance
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, providerError, status]);

  useEffect(() => {
    setIsSwitchListOpen(false);
  }, [providerError]);

  const hasReadyDocument = documents.some((d) => d.status === 'ready');

  // The error card is scoped entirely to the model that failed. `Retry` re-runs
  // that same model; the only way to reach a different one is for the user to
  // pick it themselves from the switch list below.
  const failedModelName = getModelLabel(providerError?.failedModel);
  const alternativeModels = AGENT_MODELS.filter((m) => m.id !== providerError?.failedModel);

  return (
    <div className="agent-pane">
      {/* Header */}
      <div className="pane-header">
        <div className="pane-header-title">
          <Bot size={14} />
          <span>Agent</span>
        </div>
        <div className="pane-header-actions">
          {status === 'processing' && (
            <span style={{
              fontSize: 'var(--text-xxs)',
              color: 'var(--accent)',
              fontWeight: 500,
            }}>
              Processing…
            </span>
          )}
          <button
            onClick={togglePilotMode}
            className="btn btn-ghost btn-sm"
            title="Pilot mode — controlled scenario launcher for internal testers, not shown to normal users"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              fontSize: 'var(--text-xxs)',
              color: pilotModeEnabled ? 'var(--accent)' : 'var(--text-tertiary)',
              border: pilotModeEnabled ? '1px solid var(--accent)' : '1px solid transparent',
              borderRadius: 'var(--radius-full)',
            }}
          >
            <FlaskConical size={11} />
            Pilot
          </button>
        </div>
      </div>

      {/* Pilot Scenario Launcher */}
      {pilotModeEnabled && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-2)',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-surface-secondary)',
          fontSize: 'var(--text-xxs)',
          flexWrap: 'wrap',
        }}>
          {!taskId ? (
            <>
              <select
                value={activeScenarioId ?? ''}
                onChange={(e) => e.target.value && startTask(e.target.value)}
                style={{ fontSize: 'var(--text-xxs)', padding: '2px 4px' }}
              >
                <option value="" disabled>
                  Select a pilot scenario…
                </option>
                {scenarios.map((s) => (
                  <option key={s.scenario_id} value={s.scenario_id}>
                    {s.scenario_id} — {s.task}
                  </option>
                ))}
              </select>
            </>
          ) : (
            <>
              <span style={{ color: 'var(--text-secondary)' }}>
                Task in progress: <strong>{activeScenarioId}</strong>
              </span>
              <button onClick={completeTask} className="btn btn-primary btn-sm" style={{ fontSize: 'var(--text-xxs)', padding: '2px 8px' }}>
                Mark Complete
              </button>
              <button onClick={abandonTask} className="btn btn-secondary btn-sm" style={{ fontSize: 'var(--text-xxs)', padding: '2px 8px' }}>
                Abandon
              </button>
            </>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="agent-messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title={hasReadyDocument ? 'Ask Foundation anything' : 'Upload a document to get started'}
            description={
              hasReadyDocument
                ? 'Describe what you need — analyze, compare, update, or extract information from your documents.'
                : 'Add a document — the Agent is ready as soon as it has been read.'
            }
          />
        ) : (
          messages.map((msg) => (
            <AgentMessageComponent key={msg.id} message={msg} />
          ))
        )}

        {/* Explicit Provider Error Card (No fake assistant bubble) */}
        {providerError && (
          <div
            className="agent-provider-error-card animate-fadeIn"
            data-testid="agent-provider-error-card"
            style={{
              margin: 'var(--space-3) var(--space-2)',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-surface-secondary)',
              border: '1px solid var(--border-error, #f87171)',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <AlertCircle size={16} style={{ color: 'var(--text-error, #ef4444)', flexShrink: 0 }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-xs)', color: 'var(--text-primary)' }}>
                  {errorHeadline(providerError.errorType, failedModelName)}
                </span>
              </div>
              <button
                onClick={dismissProviderError}
                className="btn btn-ghost btn-sm"
                style={{ padding: '2px', color: 'var(--text-tertiary)', lineHeight: 1 }}
                title="Dismiss error"
                data-testid="agent-error-dismiss-btn"
                aria-label="Dismiss error"
              >
                <X size={13} />
              </button>
            </div>

            <p style={{
              margin: 'var(--space-2) 0 var(--space-3)',
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)',
              lineHeight: 1.4,
            }}>
              {providerError.message} Retry {failedModelName}, or choose a different model.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <button
                onClick={retryFailedMessage}
                className="btn btn-primary btn-sm"
                data-testid="agent-error-retry-btn"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: 'var(--text-xxs)',
                  padding: '4px 10px',
                }}
              >
                <RefreshCw size={11} />
                Retry {failedModelName}
              </button>
              <button
                onClick={() => setIsSwitchListOpen((prev) => !prev)}
                className="btn btn-secondary btn-sm"
                data-testid="agent-error-switch-btn"
                aria-expanded={isSwitchListOpen}
                aria-controls="agent-error-switch-list"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: 'var(--text-xxs)',
                  padding: '4px 10px',
                }}
              >
                <ArrowRight size={11} />
                Switch Model
              </button>
            </div>

            {/* Explicit model choice. Nothing is pre-selected and nothing is
                sent until the user picks one of these by name. */}
            {isSwitchListOpen && (
              <div
                id="agent-error-switch-list"
                role="group"
                aria-label={`Switch away from ${failedModelName}`}
                data-testid="agent-error-switch-list"
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 'var(--space-1)',
                  marginTop: 'var(--space-2)',
                }}
              >
                {alternativeModels.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => switchModelAndRetry(model.id as AgentModelId)}
                    className="btn btn-ghost btn-sm"
                    data-testid={`agent-error-switch-to-${model.id}`}
                    style={{
                      fontSize: 'var(--text-xxs)',
                      padding: '3px 9px',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-full)',
                      color: 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Composer */}
      <AgentComposer />
    </div>
  );
};
