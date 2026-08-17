import React, { useEffect, useRef } from 'react';
import { List, AlertTriangle } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { EditableText } from '../shared/EditableText';

export const ElementsPane: React.FC = () => {
  const {
    targetElements,
    processingStatus,
    editError,
    editTargetElement,
    hoveredElementIndex,
    setHoveredElement,
  } = useWorkspaceStore();
  const canEdit = processingStatus === 'done';

  const rowRefs = useRef(new Map<number, HTMLTableRowElement>());

  useEffect(() => {
    if (hoveredElementIndex == null) return;
    // No-op if already visible — this only kicks in when the hover came
    // from a different pane (DocumentPane/ResultsPane).
    rowRefs.current.get(hoveredElementIndex)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [hoveredElementIndex]);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Pane Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
          <List size={16} />
          <span>ELEMENTS</span>
        </div>
        <div className="text-xs text-gray-400">{targetElements.length} elements</div>
      </div>

      {editError && (
        <div className="flex items-center space-x-2 px-3 py-1.5 bg-red-50 text-red-600 text-xs border-b border-red-200">
          <AlertTriangle size={12} className="flex-shrink-0" />
          <span>{editError}</span>
        </div>
      )}

      {/* Pane Content */}
      <div className="flex-1 overflow-auto">
        {targetElements.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-gray-400">
            {processingStatus === 'processing' ? 'Extracting elements…' : 'No elements extracted yet.'}
          </div>
        ) : (
          <table className="w-full text-sm text-left text-gray-600">
            <thead className="text-xs text-gray-400 uppercase bg-gray-50 border-b border-gray-200 sticky top-0">
              <tr>
                <th className="px-4 py-2 font-medium">#</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Element</th>
                <th className="px-4 py-2 font-medium text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {targetElements.map((el) => (
                <tr
                  key={el.index}
                  ref={(node) => {
                    if (node) rowRefs.current.set(el.index, node);
                    else rowRefs.current.delete(el.index);
                  }}
                  onMouseEnter={() => setHoveredElement(el.index)}
                  onMouseLeave={() => setHoveredElement(null)}
                  className={`border-b border-gray-100 ${
                    hoveredElementIndex === el.index ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-300' : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="px-4 py-2 font-mono text-xs">{el.index}</td>
                  <td className="px-4 py-2 capitalize">{el.type}</td>
                  <td className="px-4 py-2 max-w-[240px]">
                    <EditableText
                      value={el.text}
                      onSave={(newValue) => editTargetElement(el.index, newValue)}
                      disabled={!canEdit || el.anchor.format !== 'docx'}
                      className={`block truncate${el.source === 'manual' ? ' bg-amber-50' : ''}`}
                      title={el.source === 'manual' ? 'Manually edited' : el.text}
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    {el.confidence != null ? `${Math.round(el.confidence * 100)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
