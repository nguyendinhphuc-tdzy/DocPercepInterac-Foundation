import type { ElementRowData } from '../../../types/element';

// The contract every format-specific renderer implements. DocumentPane
// orchestrates (picks a renderer, wires callbacks to workspaceStore /
// syncStore) and must not know how any given format is actually rendered —
// see rendering/DocxRenderer.tsx, XlsxRenderer.tsx, PdfRenderer.tsx.
//
// `source` is a byte source, not a browser File specifically: DocumentPane
// fetches it from the generic per-document download endpoint (which always
// serves the document's current — patched if edited, else pristine — file,
// see foundation/api/routes/documents.py::download_document) rather than
// relying on the in-memory upload File surviving indefinitely or reflecting
// a save. A renderer must not care whether those bytes originated from a
// browser upload or a server round-trip.
export interface DocumentRendererProps {
  source: ArrayBuffer;
  // Needed to build media URLs (GET /api/documents/<session_id>/media/<doc_id>/<media_id>)
  // for embedded-image drawings — currently only XlsxRenderer uses these
  // (DOCX images render inline via docx-preview's own base64 embedding;
  // PDF pages render their own images directly via pdf.js), but they're on
  // the shared contract since any renderer could need them.
  sessionId: string;
  docId: string;
  elements: ElementRowData[];
  selectedElementIndex: number | null;
  hoveredElementIndex: number | null;
  onSelectElement: (index: number) => void;
  onHoverElement: (index: number | null) => void;
  onEditElement: (index: number, newValue: string) => void;
  editable: boolean;
}

export type RenderStatus = 'loading' | 'ready' | 'error';
