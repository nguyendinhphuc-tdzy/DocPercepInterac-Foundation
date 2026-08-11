// Mirrors foundation/perception/models.py — keep in sync manually until the
// API contract (v4 §7.5) is wired up and these can be generated instead.

export type ElementType =
  | 'heading'
  | 'table'
  | 'cell'
  | 'para'
  | 'picture'
  | 'glossary';

export interface AnchorDOCX {
  format: 'docx';
  paragraph_index: number;
  style_id: string;
  text_fingerprint: string;
  table_index?: number | null;
  row_index?: number | null;
  col_index?: number | null;
}

export interface AnchorXLSX {
  format: 'xlsx';
  sheet_name: string;
  cell_address: string;
  named_range?: string | null;
}

export interface AnchorPDF {
  format: 'pdf';
  page: number;
  bbox_relative: [number, number, number, number];
  reading_order_index: number;
}

export type Anchor = AnchorDOCX | AnchorXLSX | AnchorPDF;

export interface ElementRowData {
  index: number;
  section?: string | null;
  type: ElementType;
  name: string;
  anchor: Anchor;
  confidence?: number | null;
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
