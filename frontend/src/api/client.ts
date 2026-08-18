import type {
  Anchor,
  DocumentElementsResult,
  DocumentSummary,
  GptsMappingResult,
  PatchElementResult,
} from '../types/element';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export class ApiError extends Error {}

async function parseJsonOrThrow<T>(response: Response, unreachableMessage: string): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body?.error ?? `Request failed (HTTP ${response.status})`);
  }
  if (body === null) {
    throw new ApiError(unreachableMessage);
  }
  return body as T;
}

// ── Generic document layer — POST/GET /api/documents (api/routes/documents.py) ──
// Use-case agnostic: uploading a file only ever establishes document
// context (extract + assign anchors + classify). No role, no task, no
// mapping is ever implied by these calls.

export async function uploadDocument(file: File, sessionId: string | null): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) formData.append('session_id', sessionId);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/documents`, { method: 'POST', body: formData });
  } catch {
    throw new ApiError(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the Flask server running (foundation/api/app.py)?`
    );
  }
  return parseJsonOrThrow<DocumentSummary>(response, 'Upload failed: empty response.');
}

export async function fetchDocumentElements(
  sessionId: string,
  docId: string
): Promise<DocumentElementsResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/documents/${sessionId}/elements/${docId}`);
  } catch {
    throw new ApiError(`Could not reach the Foundation API at ${API_BASE_URL}.`);
  }
  return parseJsonOrThrow<DocumentElementsResult>(response, 'Fetching elements failed: empty response.');
}

export function downloadUrlFor(path: string): string {
  return `${API_BASE_URL}${path}`;
}

// PATCH /api/documents/<session_id>/elements/<doc_id> — writes a new value
// directly into a specific document at an element's Anchor, without
// re-running any pipeline. Works for any perceived document, not just a
// privileged "target".
export async function patchElement(
  sessionId: string,
  docId: string,
  anchor: Anchor,
  value: string
): Promise<PatchElementResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/documents/${sessionId}/elements/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anchor, value }),
    });
  } catch {
    throw new ApiError(`Could not reach the Foundation API at ${API_BASE_URL}.`);
  }
  return parseJsonOrThrow<PatchElementResult>(response, 'Edit failed: empty response.');
}

// ── GTPS-specific — POST /api/gpts/map (api/routes/gpts.py) ──
// Only ever called from an explicit GTPS action (components/gpts/) — never
// from the generic upload/document flow above. Roles are supplied
// explicitly by the caller.

export async function runGptsMapping(
  sessionId: string,
  sourceDocIds: string[],
  targetDocId: string
): Promise<GptsMappingResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/gpts/map`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        source_doc_ids: sourceDocIds,
        target_doc_id: targetDocId,
      }),
    });
  } catch {
    throw new ApiError(`Could not reach the Foundation API at ${API_BASE_URL}.`);
  }
  return parseJsonOrThrow<GptsMappingResult>(response, 'GTPS mapping failed: empty response.');
}
