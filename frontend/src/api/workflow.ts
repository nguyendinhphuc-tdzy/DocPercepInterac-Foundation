// Workflow intake API — POST/GET /api/workflow/* (foundation/api/routes/workflow.py).
//
// A workflow with a structured intake (today: Local File Roll-Forward) asks for
// named ROLES, not "some documents". Uploading still goes through the generic
// document layer in client.ts; these calls only ever attach a role to an
// already-perceived document, and read back the slot/readiness/gate state the
// server computed from the file's own content.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export class WorkflowApiError extends Error {}

export type WorkflowId = 'LOCAL_FILE_ROLL_FORWARD';

export type SlotId = 'HISTORICAL_LOCAL_FILE' | 'CURRENT_YEAR_SOURCES' | 'MASTER_TEMPLATE';

export type SlotValidationStatus =
  | 'PENDING'
  | 'ROLE_CONFIRMED'
  | 'HUMAN_REVIEW'
  | 'ROLE_MISMATCH'
  | 'FORMAT_REJECTED';

export type SlotReadinessStatus = 'EMPTY' | 'BLOCKED' | 'NEEDS_REVIEW' | 'SATISFIED';

export type DomainStatus = 'SUPPORTED' | 'HUMAN_REVIEW' | 'MISSING_SOURCE' | 'BLOCKED';

export interface SlotAssignment {
  document_id: string;
  slot_id: SlotId;
  filename: string;
  format: string;
  file_hash: string;
  version_label: string;
  file_size: number;
  perception_status: string;
  element_count: number | null;
  validation_status: SlotValidationStatus;
  detected_label: string;
  expected_label: string;
  reasons: string[];
  human_review_acknowledged: boolean;
  is_usable: boolean;
}

export interface WorkflowSlot {
  slot_id: SlotId;
  display_name: string;
  section_title: string;
  description: string;
  required: boolean;
  cardinality: 'EXACTLY_ONE' | 'ONE_OR_MORE';
  accepts_multiple: boolean;
  accepted_formats: string[];
  add_action_label: string;
  expected_label: string;
  assigned_document_ids: string[];
  validation_status: SlotValidationStatus;
  readiness_status: SlotReadinessStatus;
  assignments: SlotAssignment[];
}

export interface DomainReadiness {
  domain_id: string;
  display_name: string;
  status: DomainStatus;
  status_label: string;
  detail: string;
  supplied_by: string[];
}

export interface WorkflowGate {
  execution_allowed: boolean;
  plan_approval_allowed: boolean;
  mutation_allowed: boolean;
  message: string;
  missing_slots: string[];
  blocked_slots: string[];
  statement: string;
}

export interface WorkflowAgentContext {
  workflow: WorkflowId;
  historical_document_id: string | null;
  current_source_document_ids: string[];
  template_document_id: string | null;
  target_fiscal_year: number | null;
  historical_fiscal_year: number | null;
  inputs_complete: boolean;
  execution_allowed: boolean;
  readiness: DomainReadiness[];
}

export interface WorkflowState {
  session_id: string;
  workflow: WorkflowId;
  workflow_display_name: string;
  step: number;
  total_steps: number;
  step_label: string;
  slots: WorkflowSlot[];
  readiness: DomainReadiness[];
  gate: WorkflowGate;
  agent_context: WorkflowAgentContext;
}

async function parseOrThrow<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new WorkflowApiError(body?.error ?? `Request failed (HTTP ${response.status})`);
  }
  if (body === null) throw new WorkflowApiError('Empty response from the Foundation API.');
  return body as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new WorkflowApiError(`Could not reach the Foundation API at ${API_BASE_URL}.`);
  }
  return parseOrThrow<T>(response);
}

export function startWorkflowSession(
  sessionId: string,
  workflow: WorkflowId = 'LOCAL_FILE_ROLL_FORWARD',
): Promise<WorkflowState> {
  return request<WorkflowState>('/api/workflow/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, workflow }),
  });
}

export function fetchWorkflowState(sessionId: string): Promise<WorkflowState> {
  return request<WorkflowState>(`/api/workflow/${sessionId}`);
}

// Attaches a workflow role to an already-uploaded document. The server profiles
// the file's content and answers with the whole recomputed intake state — slot
// verdicts, readiness and gate — because one file can change all three.
export function assignDocumentToSlot(
  sessionId: string,
  slotId: SlotId,
  docId: string,
): Promise<WorkflowState & { assignment: SlotAssignment }> {
  return request(`/api/workflow/${sessionId}/slots/${slotId}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: docId }),
  });
}

export function removeDocumentFromSlot(
  sessionId: string,
  slotId: SlotId,
  docId: string,
): Promise<WorkflowState> {
  return request<WorkflowState>(
    `/api/workflow/${sessionId}/slots/${slotId}/documents/${docId}`,
    { method: 'DELETE' },
  );
}

// The explicit, recorded decision to keep a file whose role could not be
// confirmed. There is no silent-override endpoint by design.
export function keepDocumentForReview(
  sessionId: string,
  slotId: SlotId,
  docId: string,
): Promise<WorkflowState & { assignment: SlotAssignment }> {
  return request(`/api/workflow/${sessionId}/slots/${slotId}/documents/${docId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision: 'keep_for_review' }),
  });
}

// ── XLSX visual objects (audit only — GET /api/documents/.../visual-objects) ──

export interface VisualObjectKind {
  kind: string;
  display_name: string;
  count: number;
  visibility: 'RENDERED' | 'PLACEHOLDER' | 'NOT_PERCEIVED';
  reason: string;
}

export interface VisualObjectReport {
  doc_id: string;
  format: string;
  applicable: boolean;
  has_visual_objects?: boolean;
  fully_rendered?: boolean;
  status_message?: string;
  totals?: Record<string, VisualObjectKind>;
  sheets?: Array<{
    sheet_name: string;
    total_objects: number;
    unrendered_objects: number;
    objects: VisualObjectKind[];
  }>;
}

export function fetchVisualObjects(sessionId: string, docId: string): Promise<VisualObjectReport> {
  return request<VisualObjectReport>(`/api/documents/${sessionId}/visual-objects/${docId}`);
}
