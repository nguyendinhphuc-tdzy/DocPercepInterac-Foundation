// Mirrors foundation/perception/models.py — keep in sync manually until the
// API contract (v4 §7.5) is wired up and these can be generated instead.

export type ElementType =
  | 'heading'
  | 'table'
  | 'cell'
  | 'para'
  | 'picture';

export interface AnchorDOCX {
  format: 'docx';
  paragraph_index?: number | null;
  style_id: string;
  text_fingerprint: string;
  duplicate_ordinal?: number | null;
  table_index?: number | null;
  table_hash?: string | null;
  row_index?: number | null;
  col_index?: number | null;
}

export interface AnchorXLSX {
  format: 'xlsx';
  sheet_name: string;
  cell_address: string;
  named_range?: string | null;
  row_label_fingerprint?: string | null;
}

export interface AnchorPDF {
  format: 'pdf';
  page: number;
  bbox_relative: [number, number, number, number];
  reading_order_index: number;
}

export type Anchor = AnchorDOCX | AnchorXLSX | AnchorPDF;

export type ElementSource = 'text_layer' | 'ocr' | 'manual';

export interface ElementRowData {
  index: number;
  section?: string | null;
  type: ElementType;
  name: string;
  text: string;
  anchor: Anchor;
  confidence?: number | null;
  source?: ElementSource;
  tags?: string[];
}

export type TraceStage =
  | 'Geometry Layer'
  | 'Classification Layer'
  | 'User Action'
  | 'Output Engine';

export interface TraceItemData {
  id: string;
  elementId?: string | null;
  time: string;
  stage: TraceStage;
  message: string;
}

// ── Generic document layer — mirrors api/routes/documents.py ──
// Use-case agnostic: no "source"/"target" role, no mapping concept. A
// document is just something that was uploaded and perceived.

export type DocumentFormat = 'docx' | 'xlsx' | 'pdf';

// Response shape of POST /api/documents and GET /api/documents/<session_id>
// (one entry per document). Deliberately has no role/mapping fields.
export interface DocumentSummary {
  session_id: string;
  doc_id: string;
  filename: string;
  format: DocumentFormat;
  status: 'ready' | 'error';
  element_count: number;
  error: string | null;
}

// Response shape of GET /api/documents/<session_id>/elements/<doc_id> —
// elements are fetched lazily, per document, not inlined into the upload
// response (perception/api boundary keeps this a separate, cheap call).
export interface DocumentElementsResult {
  doc_id: string;
  elements: ElementRowData[];
}

export interface PatchElementResult {
  status: 'ok';
  message: string | null;
  download_url: string;
}

// One entry per live edit made via
// PATCH /api/documents/<session_id>/elements/<doc_id> — lets
// workspaceStore.ts::undoLastEdit() write the previous value back for the
// document it belongs to.
export interface EditHistoryEntry {
  docClientId: string;
  index: number;
  anchor: Anchor;
  previousValue: string;
}

// ── GTPS-specific — mirrors api/routes/gpts.py (POST /api/gpts/map) ──
// This shape is GTPS-shaped on purpose: it only ever describes the result
// of an explicit GTPS mapping run, never the generic document layer above.

export interface MappedEntry {
  source_anchor: string;
  target_anchor: string;
  target_value: string;
  confidence: number;
  timestamp: string;
  target_element_index: number | null;
}

export interface GptsMappingResult {
  session_id: string;
  source_elements: ElementRowData[];
  target_elements: ElementRowData[];
  mapped: MappedEntry[];
  download_url: string | null;
}
