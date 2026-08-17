import type { ElementRowData } from '../types/element';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export interface AgentChatRequest {
  process_id: string | null;
  message: string;
  context: {
    file_names: string[];
    selected_element: ElementRowData | null;
    element_count: number;
    mapped_count: number;
    mapped_summary: { target_anchor: string; target_value: string; confidence: number }[];
  };
}

export interface AgentChatResponse {
  response: string;
  status: 'success' | 'error';
  run_id: string | null;
  steps: { label: string; status: 'done' | 'active' | 'pending' }[];
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
    throw new Error(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the Flask server running?`
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(body?.error ?? `Agent request failed (HTTP ${response.status})`);
  }

  return body as AgentChatResponse;
}
