const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

/**
 * Four user-selectable models across two providers. This table mirrors the
 * authoritative backend registry in foundation/applications/agent/models.py —
 * the same four application-level ids on both sides. The frontend never sends
 * a raw provider deployment name; the backend resolves ids server-side.
 *
 * There is no fallback anywhere in this client. If the selected model fails,
 * the failure is surfaced as an explicit error for that model. Changing model
 * is only ever a user action.
 */
export type AgentProviderId = 'workbench' | 'gemini';

export type AgentModelId =
  | 'workbench_luna'
  | 'workbench_sol'
  | 'gemini_3_6_flash'
  | 'gemini_3_5_flash';

export const DEFAULT_AGENT_MODEL: AgentModelId = 'workbench_luna';

export interface AgentModelOption {
  id: AgentModelId;
  name: string;
  description: string;
  provider: AgentProviderId;
  group: string;
  is_default: boolean;
}

/**
 * Selector order. Gemini 3.6 Flash is listed above Gemini 3.5 Flash because it
 * is the preferred Gemini option for local/demo use — a presentation
 * preference only. It does NOT make 3.5 a fallback for 3.6.
 */
export const AGENT_MODELS: AgentModelOption[] = [
  {
    id: 'workbench_luna',
    name: 'Luna',
    description: 'Fast · Everyday tasks',
    provider: 'workbench',
    group: 'Workbench',
    is_default: true,
  },
  {
    id: 'workbench_sol',
    name: 'Sol',
    description: 'Deep reasoning · Complex analysis',
    provider: 'workbench',
    group: 'Workbench',
    is_default: false,
  },
  {
    id: 'gemini_3_6_flash',
    name: 'Gemini 3.6 Flash',
    description: 'Fast · Local/demo',
    provider: 'gemini',
    group: 'Gemini',
    is_default: false,
  },
  {
    id: 'gemini_3_5_flash',
    name: 'Gemini 3.5 Flash',
    description: 'Gemini · Alternative',
    provider: 'gemini',
    group: 'Gemini',
    is_default: false,
  },
];

/** Provider-grouped view of AGENT_MODELS, preserving the order above. */
export const AGENT_MODEL_GROUPS: { group: string; models: AgentModelOption[] }[] =
  AGENT_MODELS.reduce<{ group: string; models: AgentModelOption[] }[]>((groups, model) => {
    const existing = groups.find((g) => g.group === model.group);
    if (existing) {
      existing.models.push(model);
    } else {
      groups.push({ group: model.group, models: [model] });
    }
    return groups;
  }, []);

export function getModelOption(id: AgentModelId | undefined | null): AgentModelOption {
  return AGENT_MODELS.find((m) => m.id === id) ?? AGENT_MODELS[0];
}

/** User-facing label for a model id, used in badges and error copy. */
export function getModelLabel(id: AgentModelId | undefined | null): string {
  return getModelOption(id).name;
}

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
  model_id?: AgentModelId;
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
  model_id?: AgentModelId;
  provider?: AgentProviderId;
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
  /** The model the user selected for the request that failed — never a substitute. */
  readonly modelId?: AgentModelId;
  readonly statusCode: number;

  constructor(message: string, statusCode: number, errorType?: string, modelId?: AgentModelId) {
    super(message);
    this.name = 'AgentApiError';
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.modelId = modelId;
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
      request.model_id
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = body?.error ?? `Agent request failed (HTTP ${response.status})`;
    throw new AgentApiError(
      errorMsg,
      response.status,
      body?.error_type,
      body?.model_id ?? request.model_id
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

