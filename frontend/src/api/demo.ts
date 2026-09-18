/**
 * Demo Bridge API client — calls foundation/api/routes/demo.py exclusively.
 * ==========================================================================
 * Isolated from the production client.ts; these endpoints are prefixed
 * /api/demo/gtps/ and operate in the demo bridge's own session store.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export class DemoApiError extends Error {}

async function json<T>(res: Response, fallback: string): Promise<T> {
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new DemoApiError(body?.error ?? `Request failed (HTTP ${res.status})`);
  if (body === null) throw new DemoApiError(fallback);
  return body as T;
}

// ── Types matching demo.py's response shapes ──

export interface DemoDocInfo {
  doc_id: string;
  filename: string;
  format: string;
  size_bytes: number;
  file_hash: string;
  detected_role: string | null;
  assigned_role: string | null;
  local_path?: string;
}

export interface DemoReadiness {
  template_ready: boolean;
  historical_ready: boolean;
  current_source_ready: boolean;
  all_ready: boolean;
}

export interface DemoWorkspaceResponse {
  session_id: string;
  documents: DemoDocInfo[];
  roles: {
    TARGET_TEMPLATE: string | null;
    HISTORICAL_REFERENCE: string | null;
    CURRENT_SOURCE: string[];
  };
  readiness: DemoReadiness;
}

export interface SourceEvidence {
  source_doc_name: string;
  sheet_name: string | null;
  cell_range: string | null;
  record_count: number | null;
  matched_columns: Record<string, string>;
  reason: string | null;
}

export interface HistoricalReference {
  doc_name: string;
  table_index: number | null;
  correspondence: number | null;
}

export interface ProposedRow {
  row_idx: number;
  cells: { col_idx: number; source_sheet: string; source_cell_address: string; value: string }[];
}

export interface DemoProposal {
  id: string;
  region_id: string;
  business_target: string;
  target_region: string;
  target_table_index: number | null;
  target_table_hash: string | null;
  status: 'MAPPED' | 'NEEDS_CONFIRMATION' | 'MISSING_SOURCE' | 'UNSUPPORTED';
  status_label_vi: string;
  status_label_en: string;
  source_evidence: SourceEvidence | null;
  historical_reference: HistoricalReference | null;
  template_content: {
    initial_row_count: number | null;
    column_count: number | null;
    target_table_index: number | null;
  };
  proposed_content: string;
  proposed_rows: ProposedRow[];
  rationale: string;
  binding_verdict: string | null;
  correspondence_score: number | null;
  decision: string;
  reviewer_notes?: string;
}

export interface ReviewProjection {
  session_id: string;
  template_doc_id: string;
  template_filename: string;
  historical_doc_id: string;
  historical_filename: string;
  current_source_doc_ids: string[];
  current_source_filenames: string[];
  historical_period: string;
  current_period: string;
  summary: {
    total: number;
    mapped: number;
    needs_confirmation: number;
    missing_source: number;
    unsupported: number;
  };
  proposals: DemoProposal[];
  governance: {
    docx_mutated: boolean;
    approved_change_set_created: boolean;
    replay_executed: boolean;
    statement: string;
  };
}

// ── API calls ──

export async function createDemoWorkspace(opts: {
  sessionId?: string;
  loadLocalDemo?: boolean;
  files?: File[];
}): Promise<DemoWorkspaceResponse> {
  if (opts.loadLocalDemo || (!opts.files?.length)) {
    // JSON body for local-demo loading
    const res = await fetch(`${API_BASE}/api/demo/gtps/workspace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: opts.sessionId,
        load_local_demo: opts.loadLocalDemo ?? false,
      }),
    }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
    return json<DemoWorkspaceResponse>(res, 'Workspace creation failed.');
  }

  // Multipart upload
  const form = new FormData();
  if (opts.sessionId) form.append('session_id', opts.sessionId);
  for (const f of opts.files!) form.append('files', f);
  const res = await fetch(`${API_BASE}/api/demo/gtps/workspace`, {
    method: 'POST',
    body: form,
  }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json<DemoWorkspaceResponse>(res, 'File upload failed.');
}

export async function assignDemoRole(
  sessionId: string,
  docId: string,
  role: string | null,
): Promise<DemoWorkspaceResponse> {
  const res = await fetch(`${API_BASE}/api/demo/gtps/workspace/assign-role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, doc_id: docId, role }),
  }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json<DemoWorkspaceResponse>(res, 'Role assignment failed.');
}

export async function removeDemoDoc(
  sessionId: string,
  docId: string,
): Promise<DemoWorkspaceResponse> {
  const res = await fetch(`${API_BASE}/api/demo/gtps/workspace/remove-doc`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, doc_id: docId }),
  }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json<DemoWorkspaceResponse>(res, 'Document removal failed.');
}

export async function runDemoAnalysis(sessionId: string): Promise<ReviewProjection> {
  const res = await fetch(`${API_BASE}/api/demo/gtps/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json<ReviewProjection>(res, 'Analysis failed.');
}

export async function fetchDemoReview(sessionId: string): Promise<ReviewProjection> {
  const res = await fetch(`${API_BASE}/api/demo/gtps/review?session_id=${sessionId}`)
    .catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json<ReviewProjection>(res, 'Review fetch failed.');
}

export async function recordDemoDecision(
  sessionId: string,
  proposalId: string,
  decision: string,
  notes?: string,
): Promise<{ session_id: string; proposal_id: string; decision: string }> {
  const res = await fetch(`${API_BASE}/api/demo/gtps/review/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, proposal_id: proposalId, decision, notes }),
  }).catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json(res, 'Decision recording failed.');
}

export function demoDocContentUrl(docId: string): string {
  return `${API_BASE}/api/demo/gtps/documents/${docId}/content`;
}

export function demoDocElementsUrl(docId: string): string {
  return `${API_BASE}/api/demo/gtps/documents/${docId}/elements`;
}

export async function fetchDemoDocElements(docId: string): Promise<{ doc_id: string; elements: any[] }> {
  const res = await fetch(demoDocElementsUrl(docId))
    .catch(() => { throw new DemoApiError('Cannot reach demo API.'); });
  return json(res, 'Element fetch failed.');
}
