import React, { useEffect, useMemo, useRef } from 'react';
import { FileText, File as FileIcon, AlertTriangle, Plus, Loader2, X, ArrowRight } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { EditableText } from '../shared/EditableText';
import type { AnchorDOCX, ElementRowData } from '../../types/element';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

interface TableGroup {
  tableIndex: number;
  rows: Map<number, Map<number, ElementRowData>>;
}

// Empty-state view: no separate intake screen — documents are added right
// here. addDocument() (workspaceStore.ts) routes each file to source vs.
// target by extension, so there's no upfront "pick a role" step.
const DocumentIntake: React.FC = () => {
  const {
    sourceFiles,
    targetFiles,
    intakeError,
    processingStatus,
    processingError,
    addDocument,
    removeSourceFile,
    removeTargetFile,
    runProcessing,
  } = useWorkspaceStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const isReady = sourceFiles.length > 0 && targetFiles.length > 0;
  const hasPending = sourceFiles.length > 0 || targetFiles.length > 0;

  if (processingStatus === 'processing') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
        <Loader2 size={28} className="animate-spin mb-3" />
        <p className="text-sm">Processing…</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6 flex flex-col items-center">
      <div className="w-full max-w-sm mt-6">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full flex flex-col items-center justify-center py-10 border-2 border-dashed border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50/40 transition-colors group"
        >
          <div className="w-10 h-10 rounded-full bg-gray-100 group-hover:bg-blue-100 flex items-center justify-center mb-3 transition-colors">
            <Plus size={20} className="text-gray-500 group-hover:text-blue-600" />
          </div>
          <p className="text-sm font-medium text-gray-700">Add documents</p>
          <p className="text-xs text-gray-400 mt-1">.xlsx · .pdf · .docx</p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".xlsx,.pdf,.docx"
            className="hidden"
            onChange={(e) => {
              Array.from(e.target.files ?? []).forEach((f) => addDocument(f));
              e.target.value = '';
            }}
          />
        </button>

        {(intakeError || (processingStatus === 'error' && processingError)) && (
          <div className="mt-3 flex items-start space-x-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
            <span>{intakeError ?? processingError}</span>
          </div>
        )}

        {hasPending && (
          <div className="mt-4 space-y-1.5">
            {targetFiles.map((f, i) => (
              <div key={`t-${i}`} className="flex items-center justify-between px-3 py-2 bg-purple-50 border border-purple-100 rounded-lg">
                <div className="flex items-center space-x-2 overflow-hidden">
                  <FileText size={14} className="text-purple-500 flex-shrink-0" />
                  <div className="overflow-hidden">
                    <div className="text-xs text-gray-700 truncate">{f.name}</div>
                    <div className="text-[10px] text-purple-500 uppercase tracking-wide">Target template</div>
                  </div>
                </div>
                <button onClick={() => removeTargetFile(i)} className="text-gray-400 hover:text-red-500 flex-shrink-0">
                  <X size={13} />
                </button>
              </div>
            ))}
            {sourceFiles.map((f, i) => (
              <div key={`s-${i}`} className="flex items-center justify-between px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg">
                <div className="flex items-center space-x-2 overflow-hidden">
                  <FileIcon size={14} className="text-blue-500 flex-shrink-0" />
                  <div className="overflow-hidden">
                    <div className="text-xs text-gray-700 truncate">{f.name}</div>
                    <div className="text-[10px] text-blue-500 uppercase tracking-wide">Source data</div>
                  </div>
                </div>
                <button onClick={() => removeSourceFile(i)} className="text-gray-400 hover:text-red-500 flex-shrink-0">
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        )}

        {hasPending && (
          <button
            onClick={() => isReady && runProcessing()}
            disabled={!isReady}
            className={`mt-4 w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              isReady
                ? 'bg-gray-900 text-white hover:bg-gray-800 shadow-sm'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            <span>
              {isReady
                ? 'Start Processing'
                : `Add a ${targetFiles.length === 0 ? 'target document' : 'source file'} to continue`}
            </span>
            {isReady && <ArrowRight size={15} />}
          </button>
        )}
      </div>
    </div>
  );
};

export const DocumentPane: React.FC = () => {
  const {
    targetFiles,
    targetElements,
    processingStatus,
    editError,
    editTargetElement,
    hoveredElementIndex,
    setHoveredElement,
  } = useWorkspaceStore();
  const targetName = targetFiles.length > 0 ? targetFiles[0].name : null;
  const canEdit = processingStatus === 'done';

  const nodeRefs = useRef(new Map<number, HTMLElement>());

  useEffect(() => {
    if (hoveredElementIndex == null) return;
    nodeRefs.current.get(hoveredElementIndex)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [hoveredElementIndex]);

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
      <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
        <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
          <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
            <FileText size={16} />
            <span>DOCUMENT</span>
          </div>
        </div>
        <DocumentIntake />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
          <FileText size={16} />
          <span>DOCUMENT</span>
        </div>
        <div className="text-xs text-gray-500 truncate max-w-[200px]">{targetName}</div>
      </div>

      {editError && (
        <div className="flex items-center space-x-2 px-3 py-1.5 bg-red-50 text-red-600 text-xs border-b border-red-200">
          <AlertTriangle size={12} className="flex-shrink-0" />
          <span>{editError}</span>
        </div>
      )}

      <div className="flex-1 overflow-auto p-4 bg-white space-y-4">
        <div className="space-y-2">
          {flowElements.map((el) => (
            <div
              key={el.index}
              ref={(node) => {
                if (node) nodeRefs.current.set(el.index, node);
                else nodeRefs.current.delete(el.index);
              }}
              onMouseEnter={() => setHoveredElement(el.index)}
              onMouseLeave={() => setHoveredElement(null)}
              className={`rounded ${hoveredElementIndex === el.index ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-300' : ''}`}
            >
              <EditableText
                value={el.text}
                onSave={(newValue) => editTargetElement(el.index, newValue)}
                disabled={!canEdit}
                multiline
                className={`block ${el.type === 'heading' ? 'font-semibold text-gray-900 text-sm mt-3' : 'text-sm text-gray-700'}${el.source === 'manual' ? ' bg-amber-50' : ''}`}
                title={el.source === 'manual' ? 'Manually edited' : 'Click to edit'}
              />
            </div>
          ))}
        </div>

        {tableGroups.map((group) => {
          const rowIndices = Array.from(group.rows.keys()).sort((a, b) => a - b);
          const colCount = Math.max(
            0,
            ...rowIndices.map((r) => Math.max(0, ...Array.from(group.rows.get(r)!.keys())) + 1)
          );
          return (
            <div key={group.tableIndex} className="border border-gray-200 rounded overflow-x-auto">
              <div className="px-2 py-1 text-xs font-medium text-gray-500 bg-gray-50 border-b border-gray-200">
                Table {group.tableIndex}
              </div>
              <table className="w-full text-xs text-left text-gray-700">
                <tbody>
                  {rowIndices.map((r) => (
                    <tr key={r} className="border-b border-gray-100 last:border-b-0">
                      {Array.from({ length: colCount }, (_, c) => {
                        const cellEl = group.rows.get(r)?.get(c);
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
                            className={`px-2 py-1 border-r border-gray-100 last:border-r-0 whitespace-nowrap ${
                              cellEl && hoveredElementIndex === cellEl.index ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-300' : ''
                            }`}
                          >
                            {cellEl ? (
                              <EditableText
                                value={cellEl.text}
                                onSave={(newValue) => editTargetElement(cellEl.index, newValue)}
                                disabled={!canEdit}
                                className={cellEl.source === 'manual' ? 'bg-amber-50' : ''}
                                title={cellEl.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                              />
                            ) : (
                              ''
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
};
