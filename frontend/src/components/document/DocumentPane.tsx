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
import type { DocumentRendererProps, MappingReport } from './rendering/types';
import type { AnchorDOCX, ElementRowData } from '../../types/element';
import { idOf } from '../../utils/elementId';

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
  hoveredElementId: string | null;
  selectedElementId: string | null;
  setHoveredElement: (id: string | null) => void;
  onSelect: (id: string) => void;
  registerNode: (id: string, node: HTMLElement | null) => void;
  canEdit: boolean;
  onEdit: (elementId: string, newValue: string) => void;
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
  elements, hoveredElementId, selectedElementId, setHoveredElement, onSelect, registerNode, canEdit, onEdit,
}) => {
  const blocks = useMemo(() => buildDocumentBlocks(elements), [elements]);

  return (
    <div style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {blocks.map((block) => {
        if (block.kind === 'element') {
          const el = block.el;
          const elId = idOf(el);
          const isHighlighted = hoveredElementId === elId;
          const isSelected = selectedElementId === elId;
          return (
            <div
              key={elId}
              ref={(node) => registerNode(elId, node)}
              onMouseEnter={() => setHoveredElement(elId)}
              onMouseLeave={() => setHoveredElement(null)}
              onClick={() => onSelect(elId)}
              style={{
                padding: 'var(--space-1) var(--space-2)',
                borderRadius: 'var(--radius-md)',
                transition: 'all var(--transition-fast)',
                ...cellHighlightStyle(isSelected, isHighlighted),
              }}
            >
              <EditableText
                value={el.text}
                onSave={(newValue) => onEdit(elId, newValue)}
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
                        const cellElId = cellEl ? idOf(cellEl) : null;
                        const isHighlighted = !!cellEl && hoveredElementId === cellElId;
                        const isSelected = !!cellEl && selectedElementId === cellElId;
                        return (
                          <td
                            key={c}
                            ref={(node) => { if (cellElId) registerNode(cellElId, node); }}
                            onMouseEnter={() => cellElId && setHoveredElement(cellElId)}
                            onMouseLeave={() => cellElId && setHoveredElement(null)}
                            onClick={() => cellElId && onSelect(cellElId)}
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
                                onSave={(newValue) => cellElId && onEdit(cellElId, newValue)}
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
    editElement, hoveredElementId, setHoveredElement,
  } = useWorkspaceStore();
  const { selectedElementId, setSelectedElementId } = useSyncStore();
  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? null;
  const docName = activeDoc?.file.name ?? null;
  const activeElements = activeDoc?.elements ?? EMPTY_ELEMENTS;
  const canEdit = activeDoc?.status === 'ready' && activeDoc.elements !== null;
  const [viewMode, setViewMode] = useState<ViewMode>('original');
  const [mappingReport, setMappingReport] = useState<MappingReport | null>(null);

  // Reset the coverage summary whenever the active document changes so a
  // stale report from document A never displays while document B is shown.
  useEffect(() => { setMappingReport(null); }, [activeDoc?.docId]);

  const nodeRefs = useRef(new Map<string, HTMLElement>());
  const registerNode = (elementId: string, node: HTMLElement | null) => {
    if (node) nodeRefs.current.set(elementId, node);
    else nodeRefs.current.delete(elementId);
  };

  useEffect(() => {
    if (hoveredElementId == null) return;
    nodeRefs.current.get(hoveredElementId)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [hoveredElementId]);

  useEffect(() => {
    if (!selectedElementId) return;
    nodeRefs.current.get(selectedElementId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [selectedElementId]);

  // `editElement()`'s existing signature is array-position-based (it looks
  // up the element's current Anchor to build the PATCH body — see
  // workspaceStore.ts) — that's an implementation detail of locating the
  // element to persist, not an identity claim, so it stays index-keyed
  // internally. Every INTERACTION-facing surface (selection, hover,
  // highlight, the renderer contract) is element_id-keyed; this is the one
  // translation point between the two.
  const onEdit = (elementId: string, newValue: string) => {
    const el = activeElements.find((e) => idOf(e) === elementId);
    if (activeDocClientId && el) editElement(activeDocClientId, el.index, newValue);
  };

  const viewProps: ElementViewProps = {
    elements: activeElements,
    hoveredElementId,
    selectedElementId,
    setHoveredElement,
    onSelect: setSelectedElementId,
    registerNode,
    canEdit,
    onEdit,
  };

  const rendererProps: DocumentRendererProps = {
    source: new ArrayBuffer(0), // overwritten by OriginalRenderer for docx/pdf; unused by XlsxRenderer
    sessionId: sessionId ?? '',
    docId: activeDoc?.docId ?? '',
    elements: activeElements,
    selectedElementId,
    hoveredElementId,
    onSelectElement: setSelectedElementId,
    onHoverElement: setHoveredElement,
    onEditElement: onEdit,
    editable: canEdit,
    onMappingReport: setMappingReport,
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

      {/* Non-blocking coverage notice — a mapping shortfall never hides the
          document or disables mapped elements (failure isolation, per the
          Renderer Contract Hardening phase); this is purely informational.
          Only shown once enough of the document is affected to be worth
          surfacing, not for a couple of ambiguous notes/comments. */}
      {mappingReport && (mappingReport.byStatus.unavailable + mappingReport.byStatus.ambiguous) > Math.max(2, mappingReport.total * 0.05) && (
        <div className="renderer-notice">
          <AlertTriangle size={12} />
          <span>
            Some document elements can't be linked to the document view yet
            ({mappingReport.byStatus.unavailable + mappingReport.byStatus.ambiguous} of {mappingReport.total}).
            Everything else remains interactive.
          </span>
        </div>
      )}
      {import.meta.env.DEV && mappingReport && (
        <div style={{
          padding: 'var(--space-1) var(--space-3)', fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)',
          borderBottom: '1px solid var(--border)', fontFamily: 'monospace',
        }}>
          mapping: {mappingReport.total} total · {mappingReport.byStatus.available} available · {mappingReport.byStatus.partial} partial · {mappingReport.byStatus.unavailable} unavailable · {mappingReport.byStatus.ambiguous} ambiguous
          {' · '}
          {Object.entries(mappingReport.byType).map(([t, c]) => `${t}: ${c.available}/${c.total}`).join(', ')}
        </div>
      )}

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
