// Mirrors foundation/perception/models.py — keep in sync manually until the
// API contract (v4 §7.5) is wired up and these can be generated instead.

// Mirrors foundation/perception/models.py::ElementType exactly (wire
// values). Not every value is fully extracted/rendered/editable for every
// element that carries it — check `ElementRowData.capabilities`, never
// assume from `type` alone (see the Comprehensive Document Perception
// phase report for the taxonomy matrix).
export type ElementType =
  | 'document' | 'page' | 'section'
  | 'heading' | 'para' | 'run' | 'list' | 'list_item' | 'hyperlink' | 'bookmark'
  | 'table' | 'table_row' | 'cell'
  | 'picture' | 'image' | 'chart' | 'drawing' | 'shape' | 'text_box' | 'embedded_object'
  | 'header' | 'footer' | 'footnote' | 'endnote' | 'comment' | 'page_break' | 'section_break'
  | 'annotation' | 'form_field'
  | 'unknown';

export type ExtractionLevel = 'full' | 'partial' | 'none';

// What Foundation actually knows how to do with THIS element instance —
// distinct per instance, not implied by `type` (e.g. a DOCX chart is
// extracted="partial" while an XLSX cell is "full"). `rendered: null` means
// "not applicable to this element in this renderer" rather than "known not
// to render" (e.g. a comment isn't a visually-locatable region yet).
export interface ElementCapabilities {
  detected: boolean;
  extracted: ExtractionLevel;
  rendered: boolean | null;
  selectable: boolean;
  editable: boolean;
}

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
  // Media/drawing identity (images/charts/unrecognized drawings) — an
  // extension of this same anchor shape, not a second "docx" variant (see
  // perception/models.py::AnchorDOCX for why).
  relationship_id?: string | null;
  drawing_id?: string | null;
  media_id?: string | null;
  // Footnote/endnote/comment identity — the OOXML w:id from footnotes.xml
  // / endnotes.xml / comments.xml (see perception/models.py::AnchorDOCX.note_id).
  note_id?: string | null;
}

export interface AnchorXLSX {
  format: 'xlsx';
  sheet_name: string;
  cell_address: string;
  named_range?: string | null;
  row_label_fingerprint?: string | null;
  // Drawing identity (images/charts) — extends this same anchor shape.
  drawing_id?: string | null;
  from_cell?: string | null;
  to_cell?: string | null;
  media_id?: string | null;
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
  element_id?: string;
  parent_id?: string | null;
  section?: string | null;
  type: ElementType;
  name: string;
  text: string;
  anchor: Anchor;
  confidence?: number | null;
  source?: ElementSource;
  tags?: string[];
  capabilities?: ElementCapabilities;
}

// Mirrors foundation/perception/models.py::MediaAsset — metadata only,
// never the binary. `media_id` resolves via
// GET /api/documents/<session_id>/media/<doc_id>/<media_id>.
export interface MediaAsset {
  media_id: string;
  type: 'image' | 'chart';
  mime_type: string;
  width?: number | null;
  height?: number | null;
  source_reference: string;
}

// Mirrors foundation/perception/models.py::WorksheetMetadata — sheet-level
// display facts (not a perceivable object) an XLSX renderer needs.
export interface WorksheetMetadata {
  sheet_name: string;
  merged_ranges: string[];
  hidden_rows: number[];
  hidden_columns: string[];
  row_heights: Record<number, number>;
  column_widths: Record<string, number>;
  freeze_panes: string | null;
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
  media: MediaAsset[];
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
