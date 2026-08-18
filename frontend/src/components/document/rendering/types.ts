import type { ElementRowData } from '../../../types/element';

// The contract every format-specific renderer implements. DocumentPane
// orchestrates (picks a renderer, wires callbacks to workspaceStore /
// syncStore) and must not know how any given format is actually rendered —
// see rendering/DocxRenderer.tsx, XlsxRenderer.tsx, PdfRenderer.tsx.
//
// Identity contract (Foundation Document Perception & Renderer Contract
// Hardening phase): every interaction here is keyed by `element_id` — the
// backend's deterministic, content-derived identity (perception/
// element_classifier.py::_stable_element_id) — never by `index` (array
// position, ordering metadata only, not identity) and never by a
// renderer's own DOM/array position. A renderer resolves `element_id` to
// its OWN internal render location however it needs to (a DOM node, a grid
// cell, a canvas overlay box) — that resolution is renderer-local and must
// never leak back out as the identity itself.
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
  selectedElementId: string | null;
  hoveredElementId: string | null;
  onSelectElement: (elementId: string) => void;
  onHoverElement: (elementId: string | null) => void;
  onEditElement: (elementId: string, newValue: string) => void;
  editable: boolean;
  // Populated once mapping resolution has run — lets the pane show a
  // non-blocking coverage summary without any renderer having to expose
  // its own diagnostics UI (see DocumentPane.tsx's dev-only panel).
  onMappingReport?: (report: MappingReport) => void;
}

export type RenderStatus = 'loading' | 'ready' | 'error';

// Per-element mapping outcome — deliberately NOT a single document-level
// boolean. "available" elements stay fully interactive even when other
// elements in the same document are "unavailable"/"ambiguous" (failure
// isolation is a hard requirement of this phase — one paragraph's mapping
// failing must never disable an unrelated image or table).
export type MappingStatus = 'available' | 'partial' | 'unavailable' | 'ambiguous';

export interface MappingReport {
  total: number;
  byStatus: Record<MappingStatus, number>;
  byType: Record<string, { total: number; available: number }>;
}
