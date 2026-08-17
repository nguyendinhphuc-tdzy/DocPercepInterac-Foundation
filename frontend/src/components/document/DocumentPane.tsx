import React, { useEffect, useMemo, useRef } from 'react';
import { FileText, AlertTriangle } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { EditableText } from '../shared/EditableText';
import { EmptyState } from '../shared/EmptyState';
import type { AnchorDOCX, ElementRowData } from '../../types/element';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

interface TableGroup {
  tableIndex: number;
  rows: Map<number, Map<number, ElementRowData>>;
}

export const DocumentPane: React.FC = () => {
  const {
    targetFiles, targetElements, processingStatus, editError,
    editTargetElement, hoveredElementIndex, setHoveredElement,
  } = useWorkspaceStore();
  const { activeElementId } = useSyncStore();
  const targetName = targetFiles.length > 0 ? targetFiles[0].name : null;
  const canEdit = processingStatus === 'done';

  const nodeRefs = useRef(new Map<number, HTMLElement>());

  // Scroll to hovered or selected element
  useEffect(() => {
    const idx = hoveredElementIndex;
    if (idx == null) return;
    nodeRefs.current.get(idx)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [hoveredElementIndex]);

  // Scroll to selected element from Element Explorer
  useEffect(() => {
    if (!activeElementId) return;
    const idx = parseInt(activeElementId);
    if (!isNaN(idx)) {
      nodeRefs.current.get(idx)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeElementId]);

  const selectedIndex = activeElementId ? parseInt(activeElementId) : null;

  const { flowElements, tableGroups } = useMemo(() => {
    const flow: ElementRowData[] = [];
    const tables = new Map<number, TableGroup>();

    for (const el of targetElements) {
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
  }, [targetElements]);

  if (targetElements.length === 0) {
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
            description="Upload and analyze documents to preview their content here."
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
        {targetName && (
          <span style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-tertiary)',
            maxWidth: 200,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }} title={targetName}>
            {targetName}
          </span>
        )}
      </div>

      {editError && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-2) var(--space-3)',
          background: 'var(--error-light)',
          borderBottom: '1px solid var(--error-border)',
          fontSize: 'var(--text-xs)',
          color: 'var(--error)',
        }}>
          <AlertTriangle size={12} style={{ flexShrink: 0 }} />
          <span>{editError}</span>
        </div>
      )}

      <div className="pane-content" style={{ padding: 'var(--space-4)', background: 'var(--bg-surface)' }}>
        {/* Flow elements (headings, paragraphs) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {flowElements.map((el) => {
            const isHighlighted = hoveredElementIndex === el.index;
            const isSelected = selectedIndex === el.index;
            return (
              <div
                key={el.index}
                ref={(node) => {
                  if (node) nodeRefs.current.set(el.index, node);
                  else nodeRefs.current.delete(el.index);
                }}
                onMouseEnter={() => setHoveredElement(el.index)}
                onMouseLeave={() => setHoveredElement(null)}
                style={{
                  padding: 'var(--space-1) var(--space-2)',
                  borderRadius: 'var(--radius-md)',
                  transition: 'all var(--transition-fast)',
                  ...(isSelected ? {
                    background: 'var(--accent-light)',
                    boxShadow: 'inset 2px 0 0 var(--accent)',
                  } : isHighlighted ? {
                    background: '#EEF2FF',
                    boxShadow: 'inset 2px 0 0 var(--accent)',
                  } : {}),
                }}
              >
                <EditableText
                  value={el.text}
                  onSave={(newValue) => editTargetElement(el.index, newValue)}
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

        {/* Tables */}
        {tableGroups.map((group) => {
          const rowIndices = Array.from(group.rows.keys()).sort((a, b) => a - b);
          const colCount = Math.max(
            0,
            ...rowIndices.map((r) => Math.max(0, ...Array.from(group.rows.get(r)!.keys())) + 1)
          );
          return (
            <div key={group.tableIndex} style={{
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
              marginTop: 'var(--space-3)',
            }}>
              <div style={{
                padding: 'var(--space-2) var(--space-3)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                background: 'var(--bg-surface-secondary)',
                borderBottom: '1px solid var(--border)',
              }}>
                Table {group.tableIndex}
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: 'var(--text-xs)', borderCollapse: 'collapse' }}>
                  <tbody>
                    {rowIndices.map((r) => (
                      <tr key={r} style={{ borderBottom: '1px solid var(--border-light)' }}>
                        {Array.from({ length: colCount }, (_, c) => {
                          const cellEl = group.rows.get(r)?.get(c);
                          const isHighlighted = cellEl && hoveredElementIndex === cellEl.index;
                          const isSelected = cellEl && selectedIndex === cellEl.index;
                          return (
                            <td
                              key={c}
                              ref={(node) => {
                                if (!cellEl) return;
                                if (node) nodeRefs.current.set(cellEl.index, node);
                                else nodeRefs.current.delete(cellEl.index);
                              }}
                              onMouseEnter={() => cellEl && setHoveredElement(cellEl.index)}
                              onMouseLeave={() => cellEl && setHoveredElement(null)}
                              style={{
                                padding: 'var(--space-1) var(--space-2)',
                                borderRight: '1px solid var(--border-light)',
                                whiteSpace: 'nowrap',
                                transition: 'background var(--transition-fast)',
                                ...(isSelected ? {
                                  background: 'var(--accent-light)',
                                } : isHighlighted ? {
                                  background: '#EEF2FF',
                                } : {}),
                              }}
                            >
                              {cellEl ? (
                                <EditableText
                                  value={cellEl.text}
                                  onSave={(newValue) => editTargetElement(cellEl.index, newValue)}
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
    </div>
  );
};
