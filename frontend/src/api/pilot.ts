// Pilot instrumentation client — fire-and-forget event reporting for the
// Agent pilot phase (docs/evaluation/agent-pilot/). Must never block or
// throw into the caller: a dropped telemetry event is acceptable, a
// telemetry call breaking the Agent UI is not.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export interface PilotScenario {
  scenario_id: string;
  category: string;
  task: string;
}

export interface PilotEventFields {
  session_id?: string | null;
  pilot_session_id?: string | null;
  run_id?: string | null;
  task_id?: string | null;
  scenario_id?: string | null;
  doc_id?: string | null;
  element_id?: string | null;
  action_id?: string | null;
  status?: string;
  count?: number;
  duration_ms?: number;
  helpful?: boolean;
  reason?: string;
  comment?: string;
  confidence?: number;
  model?: string;
  previous_model?: string;
  new_model?: string;
}

export function sendPilotEvent(eventType: string, fields: PilotEventFields = {}): void {
  try {
    fetch(`${API_BASE_URL}/api/pilot/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: eventType, ...fields }),
      keepalive: true,
    }).catch(() => {
      // Swallow network errors — pilot telemetry is best-effort only.
    });
  } catch {
    // Swallow synchronous errors (e.g. fetch unavailable) for the same reason.
  }
}

export async function fetchPilotScenarios(): Promise<PilotScenario[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pilot/scenarios`);
    if (!response.ok) return [];
    const body = await response.json();
    return Array.isArray(body?.scenarios) ? body.scenarios : [];
  } catch {
    return [];
  }
}
