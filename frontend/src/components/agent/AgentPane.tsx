import React, { useRef, useEffect } from 'react';
import { Bot, Sparkles, FlaskConical } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { usePilotStore } from '../../state/pilotStore';
import { AgentComposer } from './AgentComposer';
import { AgentMessage as AgentMessageComponent } from './AgentMessage';
import { EmptyState } from '../shared/EmptyState';

export const AgentPane: React.FC = () => {
  const { messages, status } = useAgentStore();
  const { documents } = useWorkspaceStore();
  const scrollRef = useRef<HTMLDivElement>(null);
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

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Gated on Perceive (>=1 document ready), NOT on any task/execution
  // state — the Agent must be usable BEFORE any application workflow
  // (e.g. GTPS mapping) runs, so a user can state a request first.
  const hasReadyDocument = documents.some((d) => d.status === 'ready');

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

      {/* Pilot Scenario Launcher — instrumentation-only, separate from normal Agent flow */}
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
      </div>

      {/* Composer */}
      <AgentComposer />
    </div>
  );
};
