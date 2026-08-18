import React, { useRef, useEffect } from 'react';
import { Bot, Sparkles } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { AgentComposer } from './AgentComposer';
import { AgentMessage as AgentMessageComponent } from './AgentMessage';
import { EmptyState } from '../shared/EmptyState';

export const AgentPane: React.FC = () => {
  const { messages, status } = useAgentStore();
  const { documents } = useWorkspaceStore();
  const scrollRef = useRef<HTMLDivElement>(null);

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
        </div>
      </div>

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
