import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, AlertTriangle, LayoutGrid, Rows3, Columns2, Loader2, Plus } from 'lucide-react';
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

type ViewMode = 'original' | 'elements' | 'split';

// Shared per-element interaction wiring passed down to whichever view(s)
// are mounted (both mount at once in 'split' mode).
interface ElementViewProps {
  elements: ElementRowData[];
  format: 'docx' | 'xlsx' | 'pdf' | null;
  hoveredElementIndex: number | null;
  selectedIndex: number | null;
  setHoveredElement: (i: number | null) => void;
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
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, registerNode, canEdit, onEdit,
}) => {
  const { flowElements, tableGroups } = useMemo(() => {
    const flow: ElementRowData[] = [];
    const tables = new Map<number, TableGroup>();

    for (const el of elements) {
      if (el.type === 'cell' && isDocxAnchor(el.anchor) && el.anchor.table_index !== null && el.anchor.table_index !== undefined) {
        const tIdx = el.anchor.table_index;
        const rIdx = el.anchor.row_index ?? 0;
        const cIdx = el.anchor.col_index ?? 0;
        if (!tables.has(tIdx)) tables.set(tIdx, { tableIndex: tIdx, rows: new Map() });
        const group = tables.get(tIdx)!;
        if (!group.rows.has(rIdx)) group.rows.set(rIdx, new Map());
        group.rows.get(rIdx)!.set(cIdx, el);
      } else {
        flow.push(el);
      }
    }
    return { flowElements: flow, tableGroups: Array.from(tables.values()) };
  }, [elements]);

  return (
    <div style={{ padding: 'var(--space-4)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {flowElements.map((el) => {
          const isHighlighted = hoveredElementIndex === el.index;
          const isSelected = selectedIndex === el.index;
          return (
            <div
              key={el.index}
              ref={(node) => registerNode(el.index, node)}
              onMouseEnter={() => setHoveredElement(el.index)}
              onMouseLeave={() => setHoveredElement(null)}
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
        })}
      </div>

      {tableGroups.map((group) => {
        const rowIndices = Array.from(group.rows.keys()).sort((a, b) => a - b);
        const colCount = Math.max(
          0,
          ...rowIndices.map((r) => Math.max(0, ...Array.from(group.rows.get(r)!.keys())) + 1)
        );
        return (
          <div key={group.tableIndex} style={{
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
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, registerNode, canEdit, onEdit,
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

  if (sheets.size === 0) {
    return <EmptyState icon={LayoutGrid} title="No spreadsheet cells" description="This document has no XLSX cell data to display as a grid." />;
  }

  return (
    <div style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {Array.from(sheets.entries()).map(([sheetName, cells]) => {
        const maxRow = Math.max(...cells.map((c) => c.row));
        const maxCol = Math.max(...cells.map((c) => c.col));
        const byPosition = new Map(cells.map((c) => [`${c.row},${c.col}`, c.el]));
        // Guard against pathologically sparse/huge sheets blowing up the DOM.
        const cappedRow = Math.min(maxRow, 500);
        const cappedCol = Math.min(maxCol, 60);

        return (
          <div key={sheetName}>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
              {sheetName}
            </div>
            <div style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', maxHeight: 560 }}>
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
        );
      })}
    </div>
  );
};

// ── "Original" mode, PDF: grouped by page, in reading order — the
// closest practical page-oriented view without page-image rendering
// (Poppler is not installed on this deployment; see STATUS.md). ──
const PdfPageView: React.FC<ElementViewProps> = ({
  elements, hoveredElementIndex, selectedIndex, setHoveredElement, registerNode, canEdit, onEdit,
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

const OriginalView: React.FC<ElementViewProps> = (props) => {
  if (props.format === 'xlsx') return <XlsxGridView {...props} />;
  if (props.format === 'pdf') return <PdfPageView {...props} />;
  // DOCX: the flowing view already reads close to the source document —
  // present it inside a page-styled card rather than a bare list.
  return (
    <div className="document-page-card">
      <ElementsFlowView {...props} />
    </div>
  );
};

const VIEW_MODES: { mode: ViewMode; label: string; icon: React.ElementType }[] = [
  { mode: 'original', label: 'Original', icon: FileText },
  { mode: 'elements', label: 'Elements', icon: Rows3 },
  { mode: 'split', label: 'Split', icon: Columns2 },
];

// Document Pane owns document intake — this is the only file input in the
// app; there is no separate upload page. Shared by every branch below so
// "Upload documents" (empty state) and "Add documents" (header, once
// documents already exist) both open the same picker.
const ACCEPTED_EXTENSIONS = '.xlsx,.pdf,.docx';

export const DocumentPane: React.FC = () => {
  const {
    documents, activeDocClientId, editError, intakeError,
    editElement, hoveredElementIndex, setHoveredElement, addDocument,
  } = useWorkspaceStore();
  const { activeElementId } = useSyncStore();
  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? null;
  const docName = activeDoc?.file.name ?? null;
  const activeElements = activeDoc?.elements ?? EMPTY_ELEMENTS;
  const canEdit = activeDoc?.status === 'ready' && activeDoc.elements !== null;
  const [viewMode, setViewMode] = useState<ViewMode>('original');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files ?? []).forEach((f) => addDocument(f));
    e.target.value = '';
  };
  const hiddenFileInput = (
    <input
      ref={fileInputRef}
      type="file"
      multiple
      accept={ACCEPTED_EXTENSIONS}
      style={{ display: 'none' }}
      onChange={handleFilesSelected}
      aria-label="Upload documents"
    />
  );
  const intakeErrorBanner = intakeError && (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
      padding: 'var(--space-2) var(--space-3)', background: 'var(--error-light)',
      border: '1px solid var(--error-border)', borderRadius: 'var(--radius-md)',
      fontSize: 'var(--text-xs)', color: 'var(--error)', margin: 'var(--space-3)',
    }}>
      <AlertTriangle size={12} style={{ flexShrink: 0 }} />
      <span>{intakeError}</span>
    </div>
  );

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
    registerNode,
    canEdit,
    onEdit,
  };

  // No documents at all — this is the primary upload surface (there is no
  // separate intake page). Distinguished from "documents exist but none
  // active/ready yet" below: showing the same copy for both would say
  // "no document loaded" while FileRail is visibly reading real files.
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
          {hiddenFileInput}
          <EmptyState
            icon={FileText}
            title="No document loaded"
            description="Upload a document to get started."
            action={{ label: 'Upload documents', onClick: () => fileInputRef.current?.click() }}
          />
          {intakeErrorBanner}
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
          <button className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()}>
            <Plus size={12} />
            <span>Add documents</span>
          </button>
        </div>
        <div className="pane-content">
          {hiddenFileInput}
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
          {intakeErrorBanner}
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
          <button className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()}>
            <Plus size={12} />
            <span>Add documents</span>
          </button>
        </div>
        <div className="pane-content">
          {hiddenFileInput}
          <EmptyState
            icon={Loader2}
            iconClassName="animate-spin"
            title={activeDoc.status === 'perceiving' ? 'Reading document…' : 'Loading elements…'}
            description={docName ?? ''}
          />
          {intakeErrorBanner}
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
          <button className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()}>
            <Plus size={12} />
            <span>Add documents</span>
          </button>
        </div>
        <div className="pane-content">
          {hiddenFileInput}
          <EmptyState
            icon={FileText}
            title="No elements in this document"
            description="Foundation didn't extract any elements from this file."
          />
          {intakeErrorBanner}
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
          <button className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()}>
            <Plus size={12} />
            <span>Add</span>
          </button>
        </div>
      </div>

      {hiddenFileInput}
      {intakeErrorBanner}

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
