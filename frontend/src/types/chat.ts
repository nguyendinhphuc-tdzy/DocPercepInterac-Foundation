// Pane 3 — Intent/Mapping chatbox. This is the application-layer surface:
// natural language in, routed to tools (translate/extract/mapping/compare)
// that call Foundation via API. Foundation itself never sees "this is a
// translate request" — only the application layer does (v4 §6 boundary).

export type ChatRole = 'user' | 'assistant';

export type ApplicationTool = 'translate' | 'extract' | 'mapping' | 'compare';

export type ToolCallStatus = 'pending' | 'done' | 'error';

export interface ToolCall {
  tool: ApplicationTool;
  status: ToolCallStatus;
  summary?: string;
}

export interface MappingProposal {
  source: { label: string; sub: string };
  dest: { label: string; sub: string };
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  toolCalls?: ToolCall[];
  mappingProposal?: MappingProposal;
}

export const TOOL_LABELS: Record<ApplicationTool, string> = {
  translate: 'Translate',
  extract: 'Extract',
  mapping: 'Map',
  compare: 'Compare',
};
