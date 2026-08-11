import type { ChatMessage } from '../../types/chat';
import { ChatMessageBubble } from './ChatMessageBubble';

interface ChatMessageListProps {
  messages?: ChatMessage[];
}

export function ChatMessageList({ messages = [] }: ChatMessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="chat-thread">
        <div className="pane-empty-state">
          Chưa có hội thoại nào — hỏi Foundation để bắt đầu (VD: "Dịch đoạn
          này sang tiếng Việt", "Trích Doanh thu và map vào ô B2")
        </div>
      </div>
    );
  }

  return (
    <div className="chat-thread">
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
