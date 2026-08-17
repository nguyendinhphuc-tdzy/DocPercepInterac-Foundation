import type { Anchor, ProcessResult } from '../types/element';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

export class ApiError extends Error {}

export async function processDocuments(sources: File[], target: File): Promise<ProcessResult> {
  const formData = new FormData();
  for (const source of sources) {
    formData.append('source', source);
  }
  formData.append('target', target);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new ApiError(
      `Could not reach the Foundation API at ${API_BASE_URL}. Is the Flask server running (foundation/api/app.py)?`
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(body?.error ?? `Processing failed (HTTP ${response.status})`);
  }

  return body as ProcessResult;
}

export function downloadUrlFor(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export interface PatchElementResult {
  status: 'ok';
  message: string | null;
  download_url: string;
}

// PATCH /api/elements/<process_id> — writes a new value directly into the
// output document at this element's Anchor (api/routes/process.py),
// without re-running the full /api/process pipeline.
export async function patchElement(
  processId: string,
  anchor: Anchor,
  value: string
): Promise<PatchElementResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/elements/${processId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anchor, value }),
    });
  } catch {
    throw new ApiError(`Could not reach the Foundation API at ${API_BASE_URL}.`);
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(body?.error ?? `Edit failed (HTTP ${response.status})`);
  }

  return body as PatchElementResult;
}
