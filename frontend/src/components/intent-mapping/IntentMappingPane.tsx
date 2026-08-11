import { PaneHeader } from '../layout/PaneHeader';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';
import type { ChatMessage } from '../../types/chat';

interface IntentMappingPaneProps {
  messages?: ChatMessage[];
  onSend?: (text: string) => void;
}

/** Pane 3 — application-layer chatbox. Natural language in, routed to
 * translate/extract/mapping/compare tools via an LLM; Foundation only sees
 * the resulting API calls, never "this is a translate request" (v4 §6). */
export function IntentMappingPane({ messages, onSend }: IntentMappingPaneProps) {
  return (
    <div className="pane">
      <PaneHeader title="Intent / Mapping" />
      <div className="chat-pane-body">
        <ChatMessageList messages={messages} />
        <ChatInput onSend={onSend} />
      </div>
    </div>
  );
}
