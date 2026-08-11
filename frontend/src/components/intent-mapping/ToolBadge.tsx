import type { ToolCall } from '../../types/chat';
import { TOOL_LABELS } from '../../types/chat';

interface ToolBadgeProps {
  toolCall: ToolCall;
}

export function ToolBadge({ toolCall }: ToolBadgeProps) {
  return (
    <span className={`tool-badge ${toolCall.status}`}>
      {TOOL_LABELS[toolCall.tool]}
      {toolCall.status === 'pending' && '…'}
    </span>
  );
}
