import React, { useRef, useEffect } from 'react';
import { Bot, Sparkles } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { AgentComposer } from './AgentComposer';
import { AgentMessage as AgentMessageComponent } from './AgentMessage';
import { EmptyState } from '../shared/EmptyState';

export const AgentPane: React.FC = () => {
  const { messages, status } = useAgentStore();
  const { processingStatus } = useWorkspaceStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const isWorkspaceReady = processingStatus === 'done';

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
            title={isWorkspaceReady ? 'Ask Foundation anything' : 'Upload documents to get started'}
            description={
              isWorkspaceReady
                ? 'Describe what you need — analyze, compare, update, or extract information from your documents.'
                : 'Add source and target documents, then analyze them to enable the Agent.'
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
