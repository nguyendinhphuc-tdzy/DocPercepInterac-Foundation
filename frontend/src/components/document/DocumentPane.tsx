import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, AlertTriangle, Rows3, Columns2, Loader2 } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { EditableText } from '../shared/EditableText';
import { EmptyState } from '../shared/EmptyState';
import { DocxRenderer } from './rendering/DocxRenderer';
import { XlsxRenderer } from './rendering/XlsxRenderer';
import { PdfRenderer } from './rendering/PdfRenderer';
import { useDocumentBytes } from './rendering/useDocumentBytes';
import type { DocumentRendererProps } from './rendering/types';
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
// appears — used only by "Elements" mode (ElementsFlowView below). Without
// this, a naive "collect paragraphs, then collect tables" split renders
// every table AFTER every paragraph regardless of where it actually sits.
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

type ViewMode = 'original' | 'elements' | 'split';

interface ElementViewProps {
  elements: ElementRowData[];
  hoveredElementIndex: number | null;
  selectedIndex: number | null;
  setHoveredElement: (i: number | null) => void;
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

// ── "Elements" mode: Foundation's structured perception output, in
// document order — flowing paragraphs/headings + grouped DOCX tables. This
// is the ONLY mode whose source of truth is `elements[]`. "Original" mode
// (below) renders the actual uploaded document bytes instead — see
// rendering/DocxRenderer.tsx, XlsxRenderer.tsx, PdfRenderer.tsx. ──
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

const VIEW_MODES: { mode: ViewMode; label: string; icon: React.ElementType }[] = [
  { mode: 'original', label: 'Original', icon: FileText },
  { mode: 'elements', label: 'Elements', icon: Rows3 },
  { mode: 'split', label: 'Split', icon: Columns2 },
];

// ── "Original" mode: real document rendering. Fetches the document's
// current bytes (GET /api/documents/<session_id>/download/<doc_id> — always
// serves the live-patched file if one exists, else the pristine upload)
// and hands them to a format-specific renderer. XLSX is the one exception
// that stays elements[]-sourced by design — see rendering/XlsxRenderer.tsx
// for why that's still correct, not leftover reconstruction debt. ──
const OriginalRenderer: React.FC<{
  format: 'docx' | 'xlsx' | 'pdf';
  sessionId: string;
  docId: string;
  revision: number;
  rendererProps: DocumentRendererProps;
}> = ({ format, sessionId, docId, revision, rendererProps }) => {
  // XLSX doesn't need the raw file bytes at all — skip the fetch entirely.
  const needsBytes = format !== 'xlsx';
  const { status, bytes, error } = useDocumentBytes(needsBytes ? sessionId : null, needsBytes ? docId : null, revision);

  if (format === 'xlsx') return <XlsxRenderer {...rendererProps} />;

  if (status === 'loading') {
    return <EmptyState icon={Loader2} iconClassName="animate-spin" title="Loading document…" description="" />;
  }
  if (status === 'error' || !bytes) {
    return <EmptyState icon={AlertTriangle} title="Unable to load document" description={error ?? 'Could not fetch this document for rendering.'} />;
  }

  if (format === 'docx') return <DocxRenderer {...rendererProps} source={bytes} />;
  return <PdfRenderer {...rendererProps} source={bytes} />;
};

export const DocumentPane: React.FC = () => {
  const {
    documents, activeDocClientId, editError, sessionId, editHistory,
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
    hoveredElementIndex,
    selectedIndex,
    setHoveredElement,
    onSelect: (index) => setActive(String(index)),
    registerNode,
    canEdit,
    onEdit,
  };

  const rendererProps: DocumentRendererProps = {
    source: new ArrayBuffer(0), // overwritten by OriginalRenderer for docx/pdf; unused by XlsxRenderer
    sessionId: sessionId ?? '',
    docId: activeDoc?.docId ?? '',
    elements: activeElements,
    selectedElementIndex: selectedIndex,
    hoveredElementIndex,
    onSelectElement: (index) => setActive(String(index)),
    onHoverElement: setHoveredElement,
    onEditElement: onEdit,
    editable: canEdit,
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

  const canRenderOriginal = !!activeDoc.docId && !!sessionId;

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
        {viewMode === 'original' && (
          canRenderOriginal ? (
            <OriginalRenderer
              key={activeDoc.docId}
              format={activeDoc.format!}
              sessionId={sessionId!}
              docId={activeDoc.docId!}
              revision={editHistory.length}
              rendererProps={rendererProps}
            />
          ) : (
            <EmptyState icon={Loader2} iconClassName="animate-spin" title="Preparing document…" description="" />
          )
        )}
        {viewMode === 'elements' && (
          <div style={{ background: 'var(--bg-surface)' }}><ElementsFlowView {...viewProps} /></div>
        )}
        {viewMode === 'split' && (
          <div style={{ display: 'flex', height: '100%' }}>
            <div style={{ flex: 1, overflow: 'auto', borderRight: '1px solid var(--border)' }}>
              {canRenderOriginal ? (
                <OriginalRenderer
                  key={activeDoc.docId}
                  format={activeDoc.format!}
                  sessionId={sessionId!}
                  docId={activeDoc.docId!}
                  revision={editHistory.length}
                  rendererProps={rendererProps}
                />
              ) : (
                <EmptyState icon={Loader2} iconClassName="animate-spin" title="Preparing document…" description="" />
              )}
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
