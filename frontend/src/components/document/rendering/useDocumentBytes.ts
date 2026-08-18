import { useEffect, useState } from 'react';
import { downloadUrlFor } from '../../../api/client';

interface DocumentBytesState {
  status: 'loading' | 'ready' | 'error';
  bytes: ArrayBuffer | null;
  error: string | null;
}

// Fetches the document's current bytes from the generic download endpoint
// (GET /api/documents/<session_id>/download/<doc_id> — always serves the
// live-patched file if one exists, otherwise the pristine upload; see
// foundation/api/routes/documents.py::download_document). Re-fetches
// whenever `revision` changes, which callers bump after a successful edit
// so the rendered document picks up the saved write-back rather than
// showing stale pre-edit content — the DOM is never hand-patched locally.
export function useDocumentBytes(
  sessionId: string | null,
  docId: string | null,
  revision: number,
): DocumentBytesState {
  const [state, setState] = useState<DocumentBytesState>({ status: 'loading', bytes: null, error: null });

  useEffect(() => {
    if (!sessionId || !docId) {
      setState({ status: 'loading', bytes: null, error: null });
      return;
    }
    let cancelled = false;
    setState({ status: 'loading', bytes: null, error: null });

    const url = downloadUrlFor(`/api/documents/${sessionId}/download/${docId}`);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to fetch document (HTTP ${res.status})`);
        return res.arrayBuffer();
      })
      .then((buf) => {
        if (!cancelled) setState({ status: 'ready', bytes: buf, error: null });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({ status: 'error', bytes: null, error: err instanceof Error ? err.message : 'Failed to load document.' });
        }
      });

    return () => { cancelled = true; };
  }, [sessionId, docId, revision]);

  return state;
}
