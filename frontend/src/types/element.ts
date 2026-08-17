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

// Response shape of POST /api/process (foundation/api/routes/process.py) —
// applications/gpts/mapping_service.py's MappingResult, JSON-serialized.
export interface MappedEntry {
  source_anchor: string;
  target_anchor: string;
  target_value: string;
  confidence: number;
  timestamp: string;
  // Resolved server-side (applications/gpts/mapping_service.py) with the
  // same table-hash self-healing perception/anchor_builder.py uses — do
  // not re-derive this client-side from target_anchor's table_index,
  // which can be stale after drift self-heals to a different table.
  target_element_index: number | null;
}

export interface ProcessResult {
  process_id: string;
  source_elements: ElementRowData[];
  target_elements: ElementRowData[];
  mapped: MappedEntry[];
  download_url: string | null;
}

// One entry per live edit made via PATCH /api/elements/<id> — lets
// workspaceStore.ts::undoLastEdit() write the previous value back.
export interface EditHistoryEntry {
  index: number;
  anchor: Anchor;
  previousValue: string;
}
