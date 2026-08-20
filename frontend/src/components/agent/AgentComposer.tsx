import React, { useState, useRef, useCallback, useEffect } from 'react';
import { ArrowUp, Paperclip, MapPin, Sparkles, ChevronDown } from 'lucide-react';
import { useAgentStore } from '../../state/agentStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { AGENT_MODELS } from '../../api/agent';

export const AgentComposer: React.FC = () => {
  const [input, setInput] = useState('');
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  const { sendMessage, status, selectedModel, setSelectedModel } = useAgentStore();
  const { documents, activeDocClientId } = useWorkspaceStore();
  const { selectedElementId } = useSyncStore();

  const readyDocuments = documents.filter((d) => d.status === 'ready');
  const hasReadyDocument = readyDocuments.length > 0;
  const isSending = status === 'preparing' || status === 'processing';
  const canSend = input.trim().length > 0 && !isSending && hasReadyDocument;

  const activeDoc = documents.find((d) => d.clientId === activeDocClientId);
  const selectedElement = activeDoc?.elements?.find(
    (e) => e.element_id === selectedElementId
  );

  // Close model dropdown on outside click or Escape key
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (
        modelDropdownRef.current &&
        !modelDropdownRef.current.contains(e.target as Node)
      ) {
        setIsModelDropdownOpen(false);
      }
    };
    const handleDocumentKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsModelDropdownOpen(false);
      }
    };
    if (isModelDropdownOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('keydown', handleDocumentKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleDocumentKeyDown);
    };
  }, [isModelDropdownOpen]);

  const handleSubmit = useCallback((customText?: string) => {
    const textToSend = (customText ?? input).trim();
    if (!textToSend || isSending || !hasReadyDocument) return;
    sendMessage(textToSend);
    if (!customText) {
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [hasReadyDocument, input, isSending, sendMessage]);

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

  const currentModelOption = AGENT_MODELS.find((m) => m.id === selectedModel) ?? AGENT_MODELS[0];

  return (
    <div className="agent-composer">
      {/* Quick Intent Suggestion Chips */}
      {hasReadyDocument && (
        <div style={{
          display: 'flex',
          gap: 'var(--space-1)',
          padding: '0 var(--space-2) var(--space-1)',
          overflowX: 'auto',
          scrollbarWidth: 'none',
        }}>
          {selectedElement ? (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => handleSubmit('Explain and summarize the selected element')}
              style={{
                fontSize: 'var(--text-xxs)',
                padding: '2px 8px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--accent)',
                whiteSpace: 'nowrap',
              }}
            >
              <Sparkles size={10} style={{ marginRight: 4 }} />
              Explain Selection
            </button>
          ) : (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => handleSubmit('Summarize the document structure and main tables')}
              style={{
                fontSize: 'var(--text-xxs)',
                padding: '2px 8px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--text-secondary)',
                whiteSpace: 'nowrap',
              }}
            >
              <Sparkles size={10} style={{ marginRight: 4 }} />
              Summarize Document
            </button>
          )}

          <button
            className="btn btn-ghost btn-sm"
            onClick={() => handleSubmit('Find key financial and revenue metrics')}
            style={{
              fontSize: 'var(--text-xxs)',
              padding: '2px 8px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-full)',
              color: 'var(--text-secondary)',
              whiteSpace: 'nowrap',
            }}
          >
            Find Financial Metrics
          </button>
        </div>
      )}

      <div className="agent-composer-inner">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={
            hasReadyDocument
              ? selectedElement
                ? `Ask about selected ${selectedElement.name || selectedElement.type}...`
                : 'Write your request...'
              : 'Add a document first...'
          }
          disabled={!hasReadyDocument}
          rows={1}
          aria-label="Agent message input"
        />
        <button
          className="send-btn"
          onClick={() => handleSubmit()}
          disabled={!canSend}
          title="Send message (Enter)"
          aria-label="Send message"
        >
          <ArrowUp size={16} />
        </button>
      </div>

      {/* Authoritative Context Indicator & Model Selector */}
      {hasReadyDocument && (
        <div className="agent-composer-context">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Paperclip size={11} />
              <span>{readyDocuments.length} doc{readyDocuments.length === 1 ? '' : 's'}</span>
            </div>

            {selectedElement && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                color: 'var(--accent)',
                fontWeight: 500,
                background: 'var(--bg-surface)',
                padding: '1px 6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
              }}>
                <MapPin size={10} />
                <span>Selected: {selectedElement.name || selectedElement.type}</span>
              </div>
            )}
          </div>

          {/* Model Selector Dropdown */}
          <div className="agent-model-selector-container" ref={modelDropdownRef}>
            <button
              type="button"
              className="agent-model-selector-trigger"
              onClick={() => setIsModelDropdownOpen((prev) => !prev)}
              aria-haspopup="listbox"
              aria-expanded={isModelDropdownOpen}
              aria-label={`Select AI Model (currently ${currentModelOption.name})`}
              data-testid="agent-model-selector-trigger"
            >
              <span className="model-selector-label">Model</span>
              <span className="model-selector-current">{currentModelOption.name}</span>
              <ChevronDown
                size={12}
                className={`model-selector-arrow ${isModelDropdownOpen ? 'open' : ''}`}
              />
            </button>

            {isModelDropdownOpen && (
              <div
                className="agent-model-selector-dropdown animate-fadeIn"
                role="listbox"
                aria-label="Available AI Models"
                data-testid="agent-model-selector-dropdown"
              >
                {AGENT_MODELS.map((model) => {
                  const isSelected = selectedModel === model.id;
                  return (
                    <div
                      key={model.id}
                      role="option"
                      aria-selected={isSelected}
                      tabIndex={0}
                      className={`agent-model-option ${isSelected ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedModel(model.id);
                        setIsModelDropdownOpen(false);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedModel(model.id);
                          setIsModelDropdownOpen(false);
                        } else if (e.key === 'Escape') {
                          setIsModelDropdownOpen(false);
                        }
                      }}
                      data-testid={`model-option-${model.id}`}
                    >
                      <div className="model-option-radio">
                        <span className={`radio-indicator ${isSelected ? 'active' : ''}`}>
                          {isSelected ? '●' : '○'}
                        </span>
                      </div>
                      <div className="model-option-content">
                        <div className="model-option-title-row">
                          <span className="model-option-name">{model.name}</span>
                          {model.is_default && <span className="model-option-badge">Default</span>}
                        </div>
                        <span className="model-option-desc">{model.description}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

