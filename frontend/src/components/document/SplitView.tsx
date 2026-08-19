import React, { useState, useMemo } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { FileText, Rows3, File, Sheet, ArrowLeftRight, Loader2, AlertTriangle } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { DocxRenderer } from './rendering/DocxRenderer';
import { XlsxRenderer } from './rendering/XlsxRenderer';
import { PdfRenderer } from './rendering/PdfRenderer';
import { useDocumentBytes } from './rendering/useDocumentBytes';
import { EmptyState } from '../shared/EmptyState';
import { EditableText } from '../shared/EditableText';
import type { ElementRowData, AnchorDOCX, DocumentFormat } from '../../types/element';
import type { DocumentRendererProps, MappingReport } from './rendering/types';
import { idOf } from '../../utils/elementId';

function FileTypeIcon({ format, size = 13 }: { format: DocumentFormat | null; size?: number }) {
  switch (format) {
    case 'xlsx': return <Sheet size={size} style={{ color: '#2E7D32', flexShrink: 0 }} />;
    case 'pdf': return <File size={size} style={{ color: '#C62828', flexShrink: 0 }} />;
    case 'docx': return <FileText size={size} style={{ color: '#1565C0', flexShrink: 0 }} />;
    default: return <File size={size} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />;
  }
}

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

function cellHighlightStyle(isSelected: boolean, isHighlighted: boolean): React.CSSProperties {
  if (isSelected) return { background: 'var(--accent-light)', boxShadow: 'inset 2px 0 0 var(--accent)' };
  if (isHighlighted) return { background: 'var(--bg-hover)', boxShadow: 'inset 2px 0 0 var(--border)' };
  return {};
}

const SplitElementsView: React.FC<{
  elements: ElementRowData[];
  selectedElementId: string | null;
  hoveredElementId: string | null;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  canEdit: boolean;
  onEdit: (elementId: string, newValue: string) => void;
}> = ({ elements, selectedElementId, hoveredElementId, onSelect, onHover, canEdit, onEdit }) => {
  const blocks = useMemo(() => buildDocumentBlocks(elements), [elements]);

  return (
    <div style={{ padding: 'var(--space-3)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {blocks.map((block) => {
        if (block.kind === 'element') {
          const el = block.el;
          const elId = idOf(el);
          const isHighlighted = hoveredElementId === elId;
          const isSelected = selectedElementId === elId;
          return (
            <div
              key={elId}
              onMouseEnter={() => onHover(elId)}
              onMouseLeave={() => onHover(null)}
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
                    ? 'font-semibold text-gray-900 text-sm mt-2'
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
          <div key={`split-table-${group.tableIndex}`} style={{
            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
            overflow: 'hidden', marginTop: 'var(--space-2)',
          }}>
            <div style={{
              padding: 'var(--space-1) var(--space-2)', fontSize: 'var(--text-xxs)', fontWeight: 600,
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
                            onMouseEnter={() => cellElId && onHover(cellElId)}
                            onMouseLeave={() => cellElId && onHover(null)}
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

const SplitOriginalPane: React.FC<{
  sessionId: string;
  docId: string;
  format: 'docx' | 'xlsx' | 'pdf';
  revision: number;
  rendererProps: DocumentRendererProps;
}> = ({ sessionId, docId, format, revision, rendererProps }) => {
  const needsBytes = format !== 'xlsx';
  const { status, bytes, error } = useDocumentBytes(needsBytes ? sessionId : null, needsBytes ? docId : null, revision);

  if (format === 'xlsx') return <XlsxRenderer {...rendererProps} />;

  if (status === 'loading') {
    return <EmptyState icon={Loader2} iconClassName="animate-spin" title="Loading document…" description="" />;
  }
  if (status === 'error' || !bytes) {
    return <EmptyState icon={AlertTriangle} title="Unable to load document" description={error ?? 'Could not fetch bytes.'} />;
  }

  if (format === 'docx') return <DocxRenderer {...rendererProps} source={bytes} />;
  return <PdfRenderer {...rendererProps} source={bytes} />;
};

type RepresentationMode = 'original' | 'elements';

export const SplitView: React.FC<{
  onMappingReport?: (report: MappingReport) => void;
}> = ({ onMappingReport }) => {
  const {
    documents, activeDocClientId, sessionId, editHistory, editElement,
    hoveredElementId, setHoveredElement,
  } = useWorkspaceStore();
  const { selectedElementId, setSelectedElementId } = useSyncStore();

  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? documents[0] ?? null;
  const secondDoc = documents.find((d) => d.clientId !== activeDocClientId) ?? null;

  // Split state
  const [leftDocClientId, setLeftDocClientId] = useState<string>(activeDoc?.clientId ?? '');
  const [leftMode, setLeftMode] = useState<RepresentationMode>('original');
  const [rightDocClientId, setRightDocClientId] = useState<string>(secondDoc ? secondDoc.clientId : (activeDoc?.clientId ?? ''));
  const [rightMode, setRightMode] = useState<RepresentationMode>(secondDoc ? 'original' : 'elements');

  // Keep defaults updated if documents list changes
  React.useEffect(() => {
    if (activeDoc && !leftDocClientId) setLeftDocClientId(activeDoc.clientId);
    if (!rightDocClientId) setRightDocClientId(secondDoc ? secondDoc.clientId : (activeDoc?.clientId ?? ''));
  }, [activeDoc, secondDoc, leftDocClientId, rightDocClientId]);

  const leftDoc = documents.find((d) => d.clientId === leftDocClientId) ?? activeDoc;
  const rightDoc = documents.find((d) => d.clientId === rightDocClientId) ?? (secondDoc ?? activeDoc);

  const applyPreset = (preset: 'same-doc' | 'compare-orig' | 'compare-elements') => {
    if (!activeDoc) return;
    if (preset === 'same-doc') {
      setLeftDocClientId(activeDoc.clientId);
      setLeftMode('original');
      setRightDocClientId(activeDoc.clientId);
      setRightMode('elements');
    } else if (preset === 'compare-orig' && secondDoc) {
      setLeftDocClientId(activeDoc.clientId);
      setLeftMode('original');
      setRightDocClientId(secondDoc.clientId);
      setRightMode('original');
    } else if (preset === 'compare-elements' && secondDoc) {
      setLeftDocClientId(activeDoc.clientId);
      setLeftMode('elements');
      setRightDocClientId(secondDoc.clientId);
      setRightMode('elements');
    }
  };

  const handleEditLeft = (elementId: string, newValue: string) => {
    if (!leftDoc) return;
    const el = (leftDoc.elements ?? []).find((e) => idOf(e) === elementId);
    if (el) editElement(leftDoc.clientId, el.index, newValue);
  };

  const handleEditRight = (elementId: string, newValue: string) => {
    if (!rightDoc) return;
    const el = (rightDoc.elements ?? []).find((e) => idOf(e) === elementId);
    if (el) editElement(rightDoc.clientId, el.index, newValue);
  };

  const renderSideContent = (
    doc: typeof activeDoc,
    mode: RepresentationMode,
    onEdit: (elementId: string, val: string) => void,
  ) => {
    if (!doc) {
      return <EmptyState icon={FileText} title="No document selected" description="Select a document from the dropdown above." />;
    }
    if (doc.status === 'perceiving' || doc.elements === null) {
      return <EmptyState icon={Loader2} iconClassName="animate-spin" title="Reading document…" description={doc.file.name} />;
    }
    if (doc.status === 'error') {
      return <EmptyState icon={AlertTriangle} title="Document error" description={doc.error ?? 'Failed to read document.'} />;
    }

    if (mode === 'elements') {
      return (
        <div style={{ height: '100%', overflow: 'auto', background: 'var(--bg-surface)' }}>
          <SplitElementsView
            elements={doc.elements ?? EMPTY_ELEMENTS}
            selectedElementId={selectedElementId}
            hoveredElementId={hoveredElementId}
            onSelect={setSelectedElementId}
            onHover={setHoveredElement}
            canEdit={doc.status === 'ready'}
            onEdit={onEdit}
          />
        </div>
      );
    }

    // Original Mode
    const rendererProps: DocumentRendererProps = {
      source: new ArrayBuffer(0),
      sessionId: sessionId ?? '',
      docId: doc.docId ?? '',
      elements: doc.elements ?? EMPTY_ELEMENTS,
      selectedElementId,
      hoveredElementId,
      onSelectElement: setSelectedElementId,
      onHoverElement: setHoveredElement,
      onEditElement: onEdit,
      editable: doc.status === 'ready',
      onMappingReport,
    };

    return (
      <div style={{ height: '100%', overflow: 'auto', background: 'var(--bg-app)' }}>
        <SplitOriginalPane
          sessionId={sessionId ?? ''}
          docId={doc.docId ?? ''}
          format={doc.format!}
          revision={editHistory.length}
          rendererProps={rendererProps}
        />
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Quick Presets Bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--space-1) var(--space-3)', background: 'var(--bg-surface-secondary)',
        borderBottom: '1px solid var(--border)', fontSize: 'var(--text-xs)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <ArrowLeftRight size={13} style={{ color: 'var(--text-tertiary)' }} />
          <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Compare:</span>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => applyPreset('same-doc')}
            style={{ fontWeight: leftDocClientId === rightDocClientId ? 600 : 400 }}
          >
            Same Doc (Original ↔ Elements)
          </button>
          {secondDoc && (
            <>
              <span style={{ color: 'var(--border)' }}>|</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => applyPreset('compare-orig')}
                style={{ fontWeight: leftDocClientId !== rightDocClientId && leftMode === 'original' && rightMode === 'original' ? 600 : 400 }}
              >
                2 Docs (Original ↔ Original)
              </button>
              <span style={{ color: 'var(--border)' }}>|</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => applyPreset('compare-elements')}
                style={{ fontWeight: leftDocClientId !== rightDocClientId && leftMode === 'elements' && rightMode === 'elements' ? 600 : 400 }}
              >
                2 Docs (Elements ↔ Elements)
              </button>
            </>
          )}
        </div>
      </div>

      {/* 2-Pane Resizable Comparison Workspace */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <PanelGroup orientation="horizontal">
          {/* Left Pane */}
          <Panel defaultSize={50} minSize={30}>
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', borderRight: '1px solid var(--border)' }}>
              {/* Left Pane Toolbar */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: 'var(--space-1) var(--space-3)', background: 'var(--bg-surface)',
                borderBottom: '1px solid var(--border)', minHeight: 36, gap: 'var(--space-2)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
                  <FileTypeIcon format={leftDoc?.format ?? null} />
                  <select
                    value={leftDocClientId}
                    onChange={(e) => setLeftDocClientId(e.target.value)}
                    style={{
                      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-surface)', fontSize: 'var(--text-xs)',
                      padding: '2px var(--space-2)', color: 'var(--text-primary)',
                      maxWidth: 160, outline: 'none',
                    }}
                    aria-label="Left pane document"
                  >
                    {documents.map((d) => (
                      <option key={d.clientId} value={d.clientId}>{d.file.name}</option>
                    ))}
                  </select>
                </div>
                <div className="view-mode-switch" style={{ scale: '0.9', transformOrigin: 'right center' }}>
                  <button
                    className={`view-mode-btn ${leftMode === 'original' ? 'active' : ''}`}
                    onClick={() => setLeftMode('original')}
                    title="Original view"
                  >
                    <FileText size={11} />
                    <span>Original</span>
                  </button>
                  <button
                    className={`view-mode-btn ${leftMode === 'elements' ? 'active' : ''}`}
                    onClick={() => setLeftMode('elements')}
                    title="Elements view"
                  >
                    <Rows3 size={11} />
                    <span>Elements</span>
                  </button>
                </div>
              </div>
              {/* Left Content */}
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                {renderSideContent(leftDoc, leftMode, handleEditLeft)}
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />

          {/* Right Pane */}
          <Panel defaultSize={50} minSize={30}>
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              {/* Right Pane Toolbar */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: 'var(--space-1) var(--space-3)', background: 'var(--bg-surface)',
                borderBottom: '1px solid var(--border)', minHeight: 36, gap: 'var(--space-2)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
                  <FileTypeIcon format={rightDoc?.format ?? null} />
                  <select
                    value={rightDocClientId}
                    onChange={(e) => setRightDocClientId(e.target.value)}
                    style={{
                      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-surface)', fontSize: 'var(--text-xs)',
                      padding: '2px var(--space-2)', color: 'var(--text-primary)',
                      maxWidth: 160, outline: 'none',
                    }}
                    aria-label="Right pane document"
                  >
                    {documents.map((d) => (
                      <option key={d.clientId} value={d.clientId}>{d.file.name}</option>
                    ))}
                  </select>
                </div>
                <div className="view-mode-switch" style={{ scale: '0.9', transformOrigin: 'right center' }}>
                  <button
                    className={`view-mode-btn ${rightMode === 'original' ? 'active' : ''}`}
                    onClick={() => setRightMode('original')}
                    title="Original view"
                  >
                    <FileText size={11} />
                    <span>Original</span>
                  </button>
                  <button
                    className={`view-mode-btn ${rightMode === 'elements' ? 'active' : ''}`}
                    onClick={() => setRightMode('elements')}
                    title="Elements view"
                  >
                    <Rows3 size={11} />
                    <span>Elements</span>
                  </button>
                </div>
              </div>
              {/* Right Content */}
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                {renderSideContent(rightDoc, rightMode, handleEditRight)}
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};
