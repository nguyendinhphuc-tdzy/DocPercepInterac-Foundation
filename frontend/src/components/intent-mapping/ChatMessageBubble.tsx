import type { ChatMessage } from '../../types/chat';
import { ToolBadge } from './ToolBadge';
import { MappingVisual } from './MappingVisual';

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const hasTools = message.toolCalls && message.toolCalls.length > 0;

  return (
    <div className={`chat-message ${message.role}`}>
      {hasTools && (
        <div className="tool-hint-row">
          {message.toolCalls!.map((tc, i) => (
            <ToolBadge key={`${tc.tool}-${i}`} toolCall={tc} />
          ))}
        </div>
      )}
      <div className={`chat-bubble ${message.role}`}>{message.content}</div>
      {message.mappingProposal && <MappingVisual proposal={message.mappingProposal} />}
      <span className="chat-timestamp">{message.timestamp}</span>
    </div>
  );
}
