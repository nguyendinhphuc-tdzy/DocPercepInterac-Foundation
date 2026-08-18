import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, AlertTriangle, LayoutGrid, Rows3, Columns2, Loader2 } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { EditableText } from '../shared/EditableText';
import { EmptyState } from '../shared/EmptyState';
import type { AnchorDOCX, ElementRowData } from '../../types/element';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

// Stable reference for "no elements yet" — see the identical constant in
// ElementsPane.tsx for why `?? []` alone is unsafe here (a fresh empty
// array every render while a document's elements are still loading feeds
// straight into this component's own useMemo dependencies).
const EMPTY_ELEMENTS: ElementRowData[] = [];

interface TableGroup {
  tableIndex: number;
  rows: Map<number, Map<number, ElementRowData>>;
}

type DocBlock =
  | { kind: 'element'; el: ElementRowData }
  | { kind: 'table'; group: TableGroup };

// Single pass over the already-in-reading-order elements array that merges
// each DOCX table's cells into one block at the position its first cell
// appears. Without this, a naive "collect paragraphs, then collect tables"
// split (the previous approach) renders every table AFTER every paragraph
// regardless of where it actually sits in the document — losing reading
// order entirely. Shared by both Elements and Original views so both stay
// order-correct.
function buildDocumentBlocks(elements: ElementRowData[]): DocBlock[] {
  const blocks: DocBlock[] = [];
  const tablePosition = new Map<number, number>();

  for (const el of elements) {
    if (el.type === 'cell' && isDocxAnchor(el.anchor) && el.anchor.table_index !== null && el.anchor.table_index !== undefined) {
      const tIdx = el.anchor.table_index;
      const rIdx = el.anchor.row_index ?? 0;
      const cIdx = el.anchor.col_index ?? 0;
      let pos = tablePosition.get(tIdx);
      if (pos === undefined) {
        pos = blocks.length;
        blocks.push({ kind: 'table', group: { tableIndex: tIdx, rows: new Map() } });
        tablePosition.set(tIdx, pos);
      }
      const block = blocks[pos] as { kind: 'table'; group: TableGroup };
      if (!block.group.rows.has(rIdx)) block.group.rows.set(rIdx, new Map());
      block.group.rows.get(rIdx)!.set(cIdx, el);
    } else {
      blocks.push({ kind: 'element', el });
    }
  }
  return blocks;
}

// Word style IDs like "Heading1"/"Heading2" carry the heading level used
// for document typography — falls back to a mid-weight level for a
// heading-classified element with no numbered style (e.g. "Title").
function headingLevel(styleId: string | undefined): number {
  const m = /heading\s*(\d)/i.exec(styleId ?? '');
  if (m) return Math.min(parseInt(m[1], 10), 4);
  if (/title/i.test(styleId ?? '')) return 1;
  return 2;
}

type ViewMode = 'original' | 'elements' | 'split';

// Shared per-element interaction wiring passed down to whichever view(s)
// are mounted (both mount at once in 'split' mode).
interface ElementViewProps {
  elements: ElementRowData[];
  format: 'docx' | 'xlsx' | 'pdf' | null;
  hoveredElementIndex: number | null;
  selectedIndex: number | null;
  setHoveredElement: (i: number | null) => void;
  // Reverse cross-pane sync (Document → Elements): clicking an element in
  // the viewer selects the same element identity (its existing index) in
  // the Elements pane, via the same syncStore used for the Elements→Document
  // direction — no second element-ID system.
  onSelect: (index: number) => void;
  registerNode: (index: number, node: HTMLElement | null) => void;
  canEdit: boolean;
  onEdit: (index: number, newValue: string) => void;
}

function cellHighlightStyle(isSelected: boolean, isHighlighted: boolean): React.CSSProperties {
  if (isSelected) return { background: 'var(--accent-light)', boxShadow: 'inset 2px 0 0 var(--accent)' };
  if (isHighlighted) return { background: '#EEF2FF', boxShadow: 'inset 2px 0 0 var(--accent)' };
  return {};
}

// ── "Elements" mode: the Element Index in document order — flowing
// paragraphs/headings + grouped DOCX tables. Works uniformly across
// formats (XLSX/PDF elements simply have no table grouping, so they
// render as a flat flow). ──
const ElementsFlowView: React.FC<ElementViewProps> = ({
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, onSelect, registerNode, canEdit, onEdit,
}) => {
  const blocks = useMemo(() => buildDocumentBlocks(elements), [elements]);

  return (
    <div style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {blocks.map((block) => {
        if (block.kind === 'element') {
          const el = block.el;
          const isHighlighted = hoveredElementIndex === el.index;
          const isSelected = selectedIndex === el.index;
          return (
            <div
              key={el.index}
              ref={(node) => registerNode(el.index, node)}
              onMouseEnter={() => setHoveredElement(el.index)}
              onMouseLeave={() => setHoveredElement(null)}
              onClick={() => onSelect(el.index)}
              style={{
                padding: 'var(--space-1) var(--space-2)',
                borderRadius: 'var(--radius-md)',
                transition: 'all var(--transition-fast)',
                ...cellHighlightStyle(isSelected, isHighlighted),
              }}
            >
              <EditableText
                value={el.text}
                onSave={(newValue) => onEdit(el.index, newValue)}
                disabled={!canEdit}
                multiline
                className={`block ${
                  el.type === 'heading'
                    ? 'font-semibold text-gray-900 text-sm mt-3'
                    : 'text-sm text-gray-700'
                }${el.source === 'manual' ? ' bg-amber-50' : ''}`}
                title={el.source === 'manual' ? 'Manually edited' : 'Click to edit'}
              />
            </div>
          );
        }

        const group = block.group;
        const rowIndices = Array.from(group.rows.keys()).sort((a, b) => a - b);
        const colCount = Math.max(
          0,
          ...rowIndices.map((r) => Math.max(0, ...Array.from(group.rows.get(r)!.keys())) + 1)
        );
        return (
          <div key={`table-${group.tableIndex}`} style={{
            border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)',
            overflow: 'hidden', marginTop: 'var(--space-3)',
          }}>
            <div style={{
              padding: 'var(--space-2) var(--space-3)', fontSize: 'var(--text-xs)', fontWeight: 600,
              color: 'var(--text-secondary)', background: 'var(--bg-surface-secondary)',
              borderBottom: '1px solid var(--border)',
            }}>
              Table {group.tableIndex + 1}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 'var(--text-xs)', borderCollapse: 'collapse' }}>
                <tbody>
                  {rowIndices.map((r) => (
                    <tr key={r} style={{ borderBottom: '1px solid var(--border-light)' }}>
                      {Array.from({ length: colCount }, (_, c) => {
                        const cellEl = group.rows.get(r)?.get(c);
                        const isHighlighted = !!cellEl && hoveredElementIndex === cellEl.index;
                        const isSelected = !!cellEl && selectedIndex === cellEl.index;
                        return (
                          <td
                            key={c}
                            ref={(node) => cellEl && registerNode(cellEl.index, node)}
                            onMouseEnter={() => cellEl && setHoveredElement(cellEl.index)}
                            onMouseLeave={() => cellEl && setHoveredElement(null)}
                            onClick={() => cellEl && onSelect(cellEl.index)}
                            style={{
                              padding: 'var(--space-1) var(--space-2)',
                              borderRight: '1px solid var(--border-light)',
                              whiteSpace: 'nowrap',
                              transition: 'background var(--transition-fast)',
                              ...cellHighlightStyle(isSelected, isHighlighted),
                            }}
                          >
                            {cellEl ? (
                              <EditableText
                                value={cellEl.text}
                                onSave={(newValue) => onEdit(cellEl.index, newValue)}
                                disabled={!canEdit}
                                className={cellEl.source === 'manual' ? 'bg-amber-50' : ''}
                                title={cellEl.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                              />
                            ) : ''}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ── "Original" mode, XLSX: a real row/column grid parsed from each
// element's cell_address — the closest practical approximation of the
// actual spreadsheet available from data already on hand, without a new
// rendering engine/dependency. ──
function parseCellAddress(addr: string): { col: number; row: number } | null {
  const m = /^([A-Za-z]+)(\d+)$/.exec(addr);
  if (!m) return null;
  let col = 0;
  for (const ch of m[1].toUpperCase()) col = col * 26 + (ch.charCodeAt(0) - 64);
  return { col, row: parseInt(m[2], 10) };
}

function colLetter(col: number): string {
  let s = '';
  let n = col;
  while (n > 0) {
    const rem = (n - 1) % 26;
    s = String.fromCharCode(65 + rem) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

const XlsxGridView: React.FC<ElementViewProps> = ({
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, onSelect, registerNode, canEdit, onEdit,
}) => {
  const sheets = useMemo(() => {
    const bySheet = new Map<string, { el: ElementRowData; row: number; col: number }[]>();
    for (const el of elements) {
      if (el.anchor.format !== 'xlsx') continue;
      const parsed = parseCellAddress(el.anchor.cell_address);
      if (!parsed) continue;
      const list = bySheet.get(el.anchor.sheet_name) ?? [];
      list.push({ el, ...parsed });
      bySheet.set(el.anchor.sheet_name, list);
    }
    return bySheet;
  }, [elements]);

  const sheetNames = useMemo(() => Array.from(sheets.keys()), [sheets]);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  // Keep the active tab valid as the element set changes (new doc, elements
  // just finished loading, etc.) without stomping a deliberate user choice.
  const currentSheet = activeSheet && sheets.has(activeSheet) ? activeSheet : sheetNames[0] ?? null;

  if (sheets.size === 0) {
    return <EmptyState icon={LayoutGrid} title="No spreadsheet cells" description="This document has no XLSX cell data to display as a grid." />;
  }

  const cells = currentSheet ? sheets.get(currentSheet)! : [];
  const maxRow = Math.max(...cells.map((c) => c.row));
  const maxCol = Math.max(...cells.map((c) => c.col));
  const byPosition = new Map(cells.map((c) => [`${c.row},${c.col}`, c.el]));
  // Guard against pathologically sparse/huge sheets blowing up the DOM.
  const cappedRow = Math.min(maxRow, 500);
  const cappedCol = Math.min(maxCol, 60);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {sheetNames.length > 1 && (
        <div className="sheet-tabs">
          {sheetNames.map((name) => (
            <button
              key={name}
              className={`sheet-tab ${name === currentSheet ? 'active' : ''}`}
              onClick={() => setActiveSheet(name)}
            >
              {name}
            </button>
          ))}
        </div>
      )}
      <div style={{ padding: 'var(--space-4)', flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {sheetNames.length <= 1 && currentSheet && (
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
            {currentSheet}
          </div>
        )}
        <div style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', flex: 1 }}>
          <table
            style={{ borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}
            onMouseOver={(e) => {
              const cell = (e.target as HTMLElement).closest<HTMLElement>('[data-el-index]');
              if (cell) setHoveredElement(Number(cell.dataset.elIndex));
            }}
            onMouseOut={(e) => {
              const related = e.relatedTarget as HTMLElement | null;
              if (!related?.closest('[data-el-index]')) setHoveredElement(null);
            }}
          >
            <thead>
              <tr>
                <th className="xlsx-grid-corner" />
                {Array.from({ length: cappedCol }, (_, i) => (
                  <th key={i} className="xlsx-grid-colhead">{colLetter(i + 1)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: cappedRow }, (_, ri) => {
                const r = ri + 1;
                return (
                  <tr key={r}>
                    <th className="xlsx-grid-rowhead">{r}</th>
                    {Array.from({ length: cappedCol }, (_, ci) => {
                      const c = ci + 1;
                      const cellEl = byPosition.get(`${r},${c}`);
                      const isHighlighted = !!cellEl && hoveredElementIndex === cellEl.index;
                      const isSelected = !!cellEl && selectedIndex === cellEl.index;
                      return (
                        <td
                          key={c}
                          ref={(node) => cellEl && registerNode(cellEl.index, node)}
                          className="xlsx-grid-cell"
                          data-el-index={cellEl ? cellEl.index : undefined}
                          onClick={() => cellEl && onSelect(cellEl.index)}
                          style={cellHighlightStyle(isSelected, isHighlighted)}
                        >
                          {cellEl ? (
                            <EditableText
                              value={cellEl.text}
                              onSave={(newValue) => onEdit(cellEl.index, newValue)}
                              disabled={!canEdit}
                              className={cellEl.source === 'manual' ? 'bg-amber-50' : ''}
                              title={cellEl.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                            />
                          ) : ''}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {(maxRow > cappedRow || maxCol > cappedCol) && (
          <div style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
            Grid truncated to {cappedRow} rows × {cappedCol} columns for display — switch to Elements view for the full list.
          </div>
        )}
      </div>
    </div>
  );
};

// ── "Original" mode, PDF: grouped by page, in reading order — the
// closest practical page-oriented view without page-image rendering
// (Poppler is not installed on this deployment; see STATUS.md). ──
const PdfPageView: React.FC<ElementViewProps> = ({
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, onSelect, registerNode, canEdit, onEdit,
}) => {
  const pages = useMemo(() => {
    const byPage = new Map<number, ElementRowData[]>();
    for (const el of elements) {
      if (el.anchor.format !== 'pdf') continue;
      const list = byPage.get(el.anchor.page) ?? [];
      list.push(el);
      byPage.set(el.anchor.page, list);
    }
    for (const list of byPage.values()) {
      list.sort((a, b) => {
        const ra = a.anchor.format === 'pdf' ? a.anchor.reading_order_index : 0;
        const rb = b.anchor.format === 'pdf' ? b.anchor.reading_order_index : 0;
        return ra - rb;
      });
    }
    return Array.from(byPage.entries()).sort((a, b) => a[0] - b[0]);
  }, [elements]);

  if (pages.length === 0) {
    return <EmptyState icon={FileText} title="No pages" description="This document has no PDF page data to display." />;
  }

  return (
    <div style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)' }}>
        Page image preview isn't available in this deployment — showing extracted text in reading order per page.
      </div>
      {pages.map(([pageNum, pageElements]) => (
        <div key={pageNum} className="pdf-page-card">
          <div className="pdf-page-card-header">Page {pageNum}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
            {pageElements.map((el) => {
              const isHighlighted = hoveredElementIndex === el.index;
              const isSelected = selectedIndex === el.index;
              return (
                <div
                  key={el.index}
                  ref={(node) => registerNode(el.index, node)}
                  onMouseEnter={() => setHoveredElement(el.index)}
                  onMouseLeave={() => setHoveredElement(null)}
                  onClick={() => onSelect(el.index)}
                  style={{
                    padding: 'var(--space-1) var(--space-2)', borderRadius: 'var(--radius-md)',
                    ...cellHighlightStyle(isSelected, isHighlighted),
                  }}
                >
                  <EditableText
                    value={el.text}
                    onSave={(newValue) => onEdit(el.index, newValue)}
                    disabled={!canEdit}
                    multiline
                    className="text-sm text-gray-700"
                    title="PDF content is read-only"
                  />
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

const HEADING_CLASSES: Record<number, string> = {
  1: 'text-2xl font-bold text-gray-900',
  2: 'text-xl font-semibold text-gray-900',
  3: 'text-lg font-semibold text-gray-800',
  4: 'text-base font-semibold text-gray-800',
};
const BODY_PARA_CLASSES = 'text-[15px] leading-7 text-gray-700';

// ── "Original" mode, DOCX: a genuinely document-shaped view — this is a
// deliberately different component from ElementsFlowView (used by
// "Elements"), not a restyled copy of it. Real heading hierarchy, body
// paragraph typography, and full-bordered tables so the page reads as "the
// actual document", not as an extracted element list. Same block order,
// same highlight/select/edit wiring as Elements — only the presentation
// differs, per the Original/Elements split this phase requires. ──
const DocxOriginalView: React.FC<ElementViewProps> = ({
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, onSelect, registerNode, canEdit, onEdit,
}) => {
  const blocks = useMemo(() => buildDocumentBlocks(elements), [elements]);

  return (
    <div className="document-page-card">
      <div style={{ padding: 'var(--space-8) var(--space-6)' }}>
        {blocks.map((block) => {
          if (block.kind === 'element') {
            const el = block.el;
            const isHighlighted = hoveredElementIndex === el.index;
            const isSelected = selectedIndex === el.index;
            const isHeading = el.type === 'heading';
            const level = isHeading ? headingLevel(isDocxAnchor(el.anchor) ? el.anchor.style_id : undefined) : 0;
            const typographyClass = isHeading ? (HEADING_CLASSES[level] ?? HEADING_CLASSES[2]) : BODY_PARA_CLASSES;
            return (
              <div
                key={el.index}
                ref={(node) => registerNode(el.index, node)}
                onMouseEnter={() => setHoveredElement(el.index)}
                onMouseLeave={() => setHoveredElement(null)}
                onClick={() => onSelect(el.index)}
                style={{
                  padding: '2px var(--space-2)',
                  margin: '0 calc(-1 * var(--space-2))',
                  marginTop: isHeading ? 'var(--space-5)' : 0,
                  marginBottom: isHeading ? 'var(--space-2)' : 'var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  transition: 'background var(--transition-fast)',
                  ...cellHighlightStyle(isSelected, isHighlighted),
                }}
              >
                <EditableText
                  value={el.text}
                  onSave={(newValue) => onEdit(el.index, newValue)}
                  disabled={!canEdit}
                  multiline
                  className={`block ${typographyClass}${el.source === 'manual' ? ' bg-amber-50' : ''}`}
                  title={el.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                />
              </div>
            );
          }

          const group = block.group;
          const rowIndices = Array.from(group.rows.keys()).sort((a, b) => a - b);
          const colCount = Math.max(
            0,
            ...rowIndices.map((r) => Math.max(0, ...Array.from(group.rows.get(r)!.keys())) + 1)
          );
          return (
            <table
              key={`table-${group.tableIndex}`}
              className="w-full text-[14px] border-collapse"
              style={{ margin: 'var(--space-4) 0' }}
            >
              <tbody>
                {rowIndices.map((r) => (
                  <tr key={r}>
                    {Array.from({ length: colCount }, (_, c) => {
                      const cellEl = group.rows.get(r)?.get(c);
                      const isHighlighted = !!cellEl && hoveredElementIndex === cellEl.index;
                      const isSelected = !!cellEl && selectedIndex === cellEl.index;
                      return (
                        <td
                          key={c}
                          ref={(node) => cellEl && registerNode(cellEl.index, node)}
                          onMouseEnter={() => cellEl && setHoveredElement(cellEl.index)}
                          onMouseLeave={() => cellEl && setHoveredElement(null)}
                          onClick={() => cellEl && onSelect(cellEl.index)}
                          className="border border-gray-300 px-2 py-1.5 align-top"
                          style={cellHighlightStyle(isSelected, isHighlighted)}
                        >
                          {cellEl ? (
                            <EditableText
                              value={cellEl.text}
                              onSave={(newValue) => onEdit(cellEl.index, newValue)}
                              disabled={!canEdit}
                              className={`text-gray-700 ${cellEl.source === 'manual' ? 'bg-amber-50' : ''}`}
                              title={cellEl.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                            />
                          ) : ''}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })}
      </div>
    </div>
  );
};

const OriginalView: React.FC<ElementViewProps> = (props) => {
  if (props.format === 'xlsx') return <XlsxGridView {...props} />;
  if (props.format === 'pdf') return <PdfPageView {...props} />;
  return <DocxOriginalView {...props} />;
};

const VIEW_MODES: { mode: ViewMode; label: string; icon: React.ElementType }[] = [
  { mode: 'original', label: 'Original', icon: FileText },
  { mode: 'elements', label: 'Elements', icon: Rows3 },
  { mode: 'split', label: 'Split', icon: Columns2 },
];

export const DocumentPane: React.FC = () => {
  const {
    documents, activeDocClientId, editError,
    editElement, hoveredElementIndex, setHoveredElement,
  } = useWorkspaceStore();
  const { activeElementId, setActive } = useSyncStore();
  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? null;
  const docName = activeDoc?.file.name ?? null;
  const activeElements = activeDoc?.elements ?? EMPTY_ELEMENTS;
  const canEdit = activeDoc?.status === 'ready' && activeDoc.elements !== null;
  const [viewMode, setViewMode] = useState<ViewMode>('original');

  const nodeRefs = useRef(new Map<number, HTMLElement>());
  const registerNode = (index: number, node: HTMLElement | null) => {
    if (node) nodeRefs.current.set(index, node);
    else nodeRefs.current.delete(index);
  };

  useEffect(() => {
    const idx = hoveredElementIndex;
    if (idx == null) return;
    nodeRefs.current.get(idx)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [hoveredElementIndex]);

  useEffect(() => {
    if (!activeElementId) return;
    const idx = parseInt(activeElementId);
    if (!isNaN(idx)) {
      nodeRefs.current.get(idx)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeElementId]);

  const selectedIndex = activeElementId ? parseInt(activeElementId) : null;

  const onEdit = (index: number, newValue: string) => {
    if (activeDocClientId) editElement(activeDocClientId, index, newValue);
  };

  const viewProps: ElementViewProps = {
    elements: activeElements,
    format: activeDoc?.format ?? null,
    hoveredElementIndex,
    selectedIndex,
    setHoveredElement,
    onSelect: (index) => setActive(String(index)),
    registerNode,
    canEdit,
    onEdit,
  };

  // No documents at all — the Documents panel (FileRail) owns upload; this
  // pane never renders an upload control, so its layout never depends on
  // that control's width (per this phase's toolbar/intake separation).
  if (documents.length === 0) {
    return (
      <div className="pane-container">
        <div className="pane-header">
          <div className="pane-header-title">
            <FileText size={14} />
            <span>Document</span>
          </div>
        </div>
        <div className="pane-content">
          <EmptyState
            icon={FileText}
            title="No document loaded"
            description="Add a document from the Documents panel to view it here."
          />
        </div>
      </div>
    );
  }

  // Distinguish "nothing will ever be here" from "still loading" — showing
  // the same empty state for both is misleading, especially once the
  // header already reports "Ready · N elements" while this pane is still
  // mid-fetch (elements are loaded lazily per document, see
  // workspaceStore.ts::ensureElementsLoaded).
  if (!activeDoc || activeDoc.status === 'error') {
    return (
      <div className="pane-container">
        <div className="pane-header">
          <div className="pane-header-title">
            <FileText size={14} />
            <span>Document</span>
          </div>
        </div>
        <div className="pane-content">
          {activeDoc?.status === 'error' ? (
            <EmptyState
              icon={AlertTriangle}
              title="Couldn't read this document"
              description={activeDoc.error ?? 'An error occurred while reading this file.'}
            />
          ) : (
            <EmptyState
              icon={Loader2}
              iconClassName="animate-spin"
              title="Reading documents…"
              description="This will just take a moment."
            />
          )}
        </div>
      </div>
    );
  }

  if (activeDoc.status === 'perceiving' || activeDoc.elements === null) {
    return (
      <div className="pane-container">
        <div className="pane-header">
          <div className="pane-header-title">
            <FileText size={14} />
            <span>Document</span>
          </div>
        </div>
        <div className="pane-content">
          <EmptyState
            icon={Loader2}
            iconClassName="animate-spin"
            title={activeDoc.status === 'perceiving' ? 'Reading document…' : 'Loading elements…'}
            description={docName ?? ''}
          />
        </div>
      </div>
    );
  }

  if (activeElements.length === 0) {
    return (
      <div className="pane-container">
        <div className="pane-header">
          <div className="pane-header-title">
            <FileText size={14} />
            <span>Document</span>
          </div>
        </div>
        <div className="pane-content">
          <EmptyState
            icon={FileText}
            title="No elements in this document"
            description="Foundation didn't extract any elements from this file."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="pane-container">
      <div className="pane-header">
        <div className="pane-header-title">
          <FileText size={14} />
          <span>Document</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', minWidth: 0 }}>
          {docName && (
            <span style={{
              fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', maxWidth: 160,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }} title={docName}>
              {docName}
            </span>
          )}
          <div className="view-mode-switch">
            {VIEW_MODES.map(({ mode, label, icon: Icon }) => (
              <button
                key={mode}
                className={`view-mode-btn ${viewMode === mode ? 'active' : ''}`}
                onClick={() => setViewMode(mode)}
                title={`${label} view`}
              >
                <Icon size={12} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {editError && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
          padding: 'var(--space-2) var(--space-3)', background: 'var(--error-light)',
          borderBottom: '1px solid var(--error-border)', fontSize: 'var(--text-xs)', color: 'var(--error)',
        }}>
          <AlertTriangle size={12} style={{ flexShrink: 0 }} />
          <span>{editError}</span>
        </div>
      )}

      <div className="pane-content" style={{ background: 'var(--bg-app)' }}>
        {viewMode === 'original' && <OriginalView {...viewProps} />}
        {viewMode === 'elements' && (
          <div style={{ background: 'var(--bg-surface)' }}><ElementsFlowView {...viewProps} /></div>
        )}
        {viewMode === 'split' && (
          <div style={{ display: 'flex', height: '100%' }}>
            <div style={{ flex: 1, overflow: 'auto', borderRight: '1px solid var(--border)' }}>
              <OriginalView {...viewProps} />
            </div>
            <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-surface)' }}>
              <ElementsFlowView {...viewProps} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
