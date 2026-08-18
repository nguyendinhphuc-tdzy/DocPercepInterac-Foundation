import React, { useState, useRef, useCallback } from 'react';
import { ArrowUp } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';

export const AgentComposer: React.FC = () => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, status } = useAgentStore();
  const { documents } = useWorkspaceStore();

  // Gated on Perceive (>=1 document ready), never on a task/execution
  // state — this is what lets the user state a request BEFORE any
  // application workflow runs (Perceive -> user states intent -> Execute).
  const hasReadyDocument = documents.some((d) => d.status === 'ready');
  const isSending = status === 'preparing' || status === 'processing';
  const canSend = input.trim().length > 0 && !isSending && hasReadyDocument;

  const handleSubmit = useCallback(() => {
    if (!canSend) return;
    sendMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [canSend, input, sendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  // Auto-resize textarea
  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }, []);

  return (
    <div className="agent-composer">
      <div className="agent-composer-inner">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={
            hasReadyDocument
              ? 'Write your request...'
              : 'Add a document first...'
          }
          disabled={!hasReadyDocument}
          rows={1}
          aria-label="Agent message input"
        />
        <button
          className="send-btn"
          onClick={handleSubmit}
          disabled={!canSend}
          title="Send message (Enter)"
          aria-label="Send message"
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </div>
  );
};
