const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export type AgentModelId = 'luna' | 'sol';

export interface AgentModelOption {
  id: AgentModelId;
  name: string;
  description: string;
  is_default: boolean;
}

export const AGENT_MODELS: AgentModelOption[] = [
  {
    id: 'luna',
    name: 'Luna',
    description: 'Fast · Everyday tasks',
    is_default: true,
  },
  {
    id: 'sol',
    name: 'Sol',
    description: 'Deep reasoning · Complex analysis',
    is_default: false,
  },
];

export interface Citation {
  doc_id: string;
  doc_name?: string;
  element_id: string;
  element_name: string;
  type: string;
  text_snippet?: string;
}

export interface ProposedAction {
  action_id: string;
  type: 'update_element' | 'batch_update';
  doc_id: string;
  doc_name: string;
  element_id: string;
  element_name: string;
  current_value: string;
  proposed_value: string;
  rationale: string;
  requires_confirmation: boolean;
  status: 'proposed' | 'applied' | 'rejected' | 'expired' | 'stale' | 'failed';
}

export interface AgentStep {
  label: string;
  status: 'done' | 'active' | 'pending';
}

export interface AgentChatRequest {
  session_id: string | null;
  message: string;
  model?: AgentModelId;
  context: {
    active_doc_id?: string | null;
    selected_element_id?: string | null;
    file_names?: string[];
    element_count?: number;
  };
}

export interface AgentChatResponse {
  response: string;
  status: 'success' | 'error';
  run_id: string | null;
  intent?: string;
  model?: AgentModelId;
  steps: AgentStep[];
  citations?: Citation[];
  proposed_actions?: ProposedAction[];
  error?: string;
}

export interface ExecuteActionRequest {
  session_id: string;
  action_id: string;
}

export interface ExecuteActionResponse {
  status: 'success' | 'rejected' | 'error';
  action_id: string;
  doc_id: string;
  element_id: string;
  old_value: string;
  new_value: string;
  download_url?: string;
  self_heal?: string | null;
  error?: string;
}

export interface RejectActionRequest {
  session_id: string;
  action_id: string;
}

export interface RejectActionResponse {
  status: 'rejected';
  action_id: string;
  error?: string;
}

export class AgentApiError extends Error {
  readonly errorType?: string;
  readonly model?: AgentModelId;
  readonly statusCode: number;

  constructor(message: string, statusCode: number, errorType?: string, model?: AgentModelId) {
    super(message);
    this.name = 'AgentApiError';
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.model = model;
  }
}

export async function sendAgentChat(request: AgentChatRequest): Promise<AgentChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch {
    throw new AgentApiError(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the server running?`,
      0,
      'network_error',
      request.model
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = body?.error ?? `Agent request failed (HTTP ${response.status})`;
    throw new AgentApiError(
      errorMsg,
      response.status,
      body?.error_type,
      body?.model ?? request.model
    );
  }

  return body as AgentChatResponse;
}

export async function executeAgentAction(request: ExecuteActionRequest): Promise<ExecuteActionResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/agent/action/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the Flask server running?`
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(body?.error ?? `Action execution failed (HTTP ${response.status})`);
  }

  return body as ExecuteActionResponse;
}

export async function rejectAgentAction(request: RejectActionRequest): Promise<RejectActionResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/agent/action/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the Flask server running?`
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(body?.error ?? `Action rejection failed (HTTP ${response.status})`);
  }

  return body as RejectActionResponse;
}

