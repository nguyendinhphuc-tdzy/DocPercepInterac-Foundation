import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { FileText, AlertTriangle, Rows3, Columns2, Loader2, ZoomIn, ZoomOut, X, Info } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { EditableText } from '../shared/EditableText';
import { EmptyState } from '../shared/EmptyState';
import { DocxRenderer } from './rendering/DocxRenderer';
import { XlsxRenderer } from './rendering/XlsxRenderer';
import { PdfRenderer } from './rendering/PdfRenderer';
import { useDocumentBytes } from './rendering/useDocumentBytes';
import { SplitView } from './SplitView';
import type { DocumentRendererProps, MappingReport } from './rendering/types';
import type { AnchorDOCX, ElementRowData } from '../../types/element';
import { idOf } from '../../utils/elementId';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

const EMPTY_ELEMENTS: ElementRowData[] = [];

interface TableGroup {
  tableIndex: number;
  rows: Map<number, Map<number, ElementRowData>>;
}

type DocBlock =
  | { kind: 'element'; el: ElementRowData }
  | { kind: 'table'; group: TableGroup };

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
  if (isHighlighted) return { background: 'var(--bg-hover)', boxShadow: 'inset 2px 0 0 var(--border)' };
  return {};
}

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
                cursor: 'pointer',
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
                              cursor: cellEl ? 'pointer' : 'default',
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

const OriginalRenderer: React.FC<{
  format: 'docx' | 'xlsx' | 'pdf';
  sessionId: string;
  docId: string;
  revision: number;
  rendererProps: DocumentRendererProps;
}> = ({ format, sessionId, docId, revision, rendererProps }) => {
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
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Global Escape shortcut: deselect current element when not in active input/textarea
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const target = e.target as HTMLElement | null;
        const isEditing = target?.tagName === 'TEXTAREA' || target?.tagName === 'INPUT';
        if (!isEditing && selectedElementId != null) {
          setSelectedElementId(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedElementId, setSelectedElementId]);

  // Reset mapping report on document switch
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

  const onEdit = (elementId: string, newValue: string) => {
    const el = activeElements.find((e) => idOf(e) === elementId);
    if (activeDocClientId && el) editElement(activeDocClientId, el.index, newValue);
  };

  const handleZoomIn = useCallback(() => {
    setZoomLevel((z) => Math.min(z + 15, 175));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((z) => Math.max(z - 15, 60));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoomLevel(100);
  }, []);

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
    source: new ArrayBuffer(0),
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
  const selectedElement = selectedElementId != null ? activeElements.find((e) => idOf(e) === selectedElementId) : null;

  return (
    <div className="pane-container">
      {/* Pane Header */}
      <div className="pane-header">
        <div className="pane-header-title">
          <FileText size={14} />
          <span>Document</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
          {/* Zoom controls (for original and elements modes) */}
          {viewMode !== 'split' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: 'var(--bg-app)', padding: '2px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
              <button
                className="btn btn-ghost btn-sm btn-icon"
                onClick={handleZoomOut}
                title="Zoom out"
                aria-label="Zoom out"
              >
                <ZoomOut size={12} />
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleResetZoom}
                title="Reset zoom to 100%"
                style={{ fontSize: 'var(--text-xxs)', padding: '0 4px', minWidth: 36, textAlign: 'center' }}
              >
                {zoomLevel}%
              </button>
              <button
                className="btn btn-ghost btn-sm btn-icon"
                onClick={handleZoomIn}
                title="Zoom in"
                aria-label="Zoom in"
              >
                <ZoomIn size={12} />
              </button>
            </div>
          )}

          {/* View mode switcher */}
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

          {/* Dev Diagnostics Toggle */}
          {import.meta.env.DEV && mappingReport && (
            <button
              className="btn btn-ghost btn-sm btn-icon"
              onClick={() => setShowDiagnostics(!showDiagnostics)}
              title="Toggle perception & mapping diagnostics"
              aria-label="Toggle diagnostics"
              style={{ color: showDiagnostics ? 'var(--accent)' : 'var(--text-tertiary)' }}
            >
              <Info size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Selected Element Action Bar (Contextual Deselection & Info) */}
      {selectedElement && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: 'var(--space-1) var(--space-3)', background: 'var(--accent-light)',
          borderBottom: '1px solid var(--accent-border)', fontSize: 'var(--text-xs)',
          color: 'var(--accent)', animation: 'fadeIn 120ms ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
            <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{selectedElement.type}:</span>
            <span style={{
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              maxWidth: 320, color: 'var(--text-primary)',
            }}>
              {selectedElement.text || selectedElement.name}
            </span>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setSelectedElementId(null)}
            title="Deselect (Escape)"
            style={{ display: 'flex', alignItems: 'center', gap: '2px', color: 'var(--accent)', fontWeight: 500 }}
          >
            <span>Deselect</span>
            <X size={12} />
          </button>
        </div>
      )}

      {/* Dev Diagnostics Drawer (Collapsible) */}
      {showDiagnostics && mappingReport && (
        <div style={{
          padding: 'var(--space-2) var(--space-3)', fontSize: 'var(--text-xxs)', color: 'var(--text-secondary)',
          background: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--border)', fontFamily: 'var(--font-mono)',
          display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', alignItems: 'center',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--accent)' }}>Mapping Report:</span>
          <span>{mappingReport.total} total</span>
          <span>· {mappingReport.byStatus.available} available ({(mappingReport.byStatus.available / mappingReport.total * 100).toFixed(1)}%)</span>
          {mappingReport.byStatus.partial > 0 && <span>· {mappingReport.byStatus.partial} partial</span>}
          {mappingReport.byStatus.unavailable > 0 && <span style={{ color: 'var(--error)' }}>· {mappingReport.byStatus.unavailable} unavailable</span>}
          {mappingReport.byStatus.ambiguous > 0 && <span style={{ color: 'var(--warning)' }}>· {mappingReport.byStatus.ambiguous} ambiguous</span>}
          <div style={{ width: '100%', borderTop: '1px dashed var(--border)', paddingTop: 2, marginTop: 2, color: 'var(--text-tertiary)' }}>
            {Object.entries(mappingReport.byType).map(([t, c]) => `${t}: ${c.available}/${c.total}`).join(' · ')}
          </div>
        </div>
      )}

      {/* Non-blocking coverage notice */}
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

      {/* Main Document Content */}
      <div
        className="pane-content"
        style={{ background: 'var(--bg-app)', position: 'relative' }}
        onPointerDown={(e) => {
          // Deselect on neutral container clicks (if clicked on root background directly)
          if (e.target === e.currentTarget && selectedElementId != null) {
            setSelectedElementId(null);
          }
        }}
      >
        {viewMode === 'original' && (
          canRenderOriginal ? (
            <div
              style={{
                height: '100%',
                transform: zoomLevel !== 100 ? `scale(${zoomLevel / 100})` : undefined,
                transformOrigin: 'top center',
                transition: 'transform var(--transition-fast)',
              }}
            >
              <OriginalRenderer
                key={activeDoc.docId}
                format={activeDoc.format!}
                sessionId={sessionId!}
                docId={activeDoc.docId!}
                revision={editHistory.length}
                rendererProps={rendererProps}
              />
            </div>
          ) : (
            <EmptyState icon={Loader2} iconClassName="animate-spin" title="Preparing document…" description="" />
          )
        )}
        {viewMode === 'elements' && (
          <div
            style={{
              background: 'var(--bg-surface)', minHeight: '100%',
              transform: zoomLevel !== 100 ? `scale(${zoomLevel / 100})` : undefined,
              transformOrigin: 'top center',
              transition: 'transform var(--transition-fast)',
            }}
          >
            <ElementsFlowView {...viewProps} />
          </div>
        )}
        {viewMode === 'split' && (
          <SplitView onMappingReport={setMappingReport} />
        )}
      </div>
    </div>
  );
};
