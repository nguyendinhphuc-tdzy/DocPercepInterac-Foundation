import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { ApplicationTool } from '../../types/chat';
import { TOOL_LABELS } from '../../types/chat';

const AVAILABLE_TOOLS: ApplicationTool[] = ['translate', 'extract', 'mapping', 'compare'];

interface ChatInputProps {
  onSend?: (text: string) => void;
}

/** Chat entry point for the application layer — routes intent to
 * translate/extract/mapping/compare tools via an LLM (OpenAI/Workbench).
 * Foundation itself never sees which tool this is (v4 §6 boundary). */
export function ChatInput({ onSend }: ChatInputProps) {
  const [value, setValue] = useState('');
  const wired = Boolean(onSend);

  const handleSend = () => {
    if (!value.trim() || !onSend) return;
    onSend(value.trim());
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <div className="tool-hint-row">
        {AVAILABLE_TOOLS.map((tool) => (
          <span key={tool} className="tool-badge idle">
            {TOOL_LABELS[tool]}
          </span>
        ))}
      </div>
      <div className="chat-input-row">
        <textarea
          className="chat-textarea"
          placeholder="VD: Trích giá trị Doanh thu từ bảng và map vào ô B2..."
          rows={2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="btn-primary"
          disabled={!wired}
          title={wired ? undefined : 'Chưa nối OpenAI/Workbench — application layer chưa build'}
          onClick={handleSend}
        >
          Gửi
        </button>
      </div>
    </div>
  );
}
