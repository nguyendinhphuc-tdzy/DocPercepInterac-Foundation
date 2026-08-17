import React from 'react';
import { Bot, User, CheckCircle, Loader2, Circle } from 'lucide-react';
import type { AgentMessage as AgentMessageType } from '../../state/agentStore';

interface AgentMessageProps {
  message: AgentMessageType;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

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
        <div className={`agent-bubble ${message.role}`}>
          {message.content}
        </div>

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
