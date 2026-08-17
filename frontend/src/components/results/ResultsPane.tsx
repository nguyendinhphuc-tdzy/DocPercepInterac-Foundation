import React from 'react';
import { CheckCircle, Download } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { downloadUrlFor } from '../../api/client';

export const ResultsPane: React.FC = () => {
  const { mapped, downloadUrl, processingStatus, hoveredElementIndex, setHoveredElement } = useWorkspaceStore();

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Pane Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
          <CheckCircle size={16} />
          <span>RESULTS</span>
        </div>
        {downloadUrl && (
          <a
            href={downloadUrlFor(downloadUrl)}
            className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-800"
          >
            <Download size={12} />
            <span>Download patched DOCX</span>
          </a>
        )}
      </div>

      <div className="flex flex-col h-full overflow-hidden">
        {/* Output Section */}
        <div className="flex-1 p-4 overflow-auto border-b border-gray-200">
          <div className="text-xs font-semibold text-gray-400 uppercase mb-3">Output ({mapped.length} mapped)</div>
          {mapped.length === 0 ? (
            <div className="text-sm text-gray-400">
              {processingStatus === 'processing' && 'Mapping…'}
              {processingStatus === 'idle' && 'Add documents in the Document pane to get started.'}
              {processingStatus === 'error' && 'Processing failed — see the Document pane for details.'}
              {processingStatus === 'done' &&
                'No rule matched this document pair — the demo mapping rules are hard-coded for one specific client template.'}
            </div>
          ) : (
            <div className="font-mono text-sm text-gray-700 bg-gray-50 p-3 rounded border border-gray-100 space-y-1">
              {mapped.map((m, i) => (
                <div
                  key={i}
                  onMouseEnter={() => m.target_element_index != null && setHoveredElement(m.target_element_index)}
                  onMouseLeave={() => m.target_element_index != null && setHoveredElement(null)}
                  className={`flex justify-between border-b border-gray-200 last:border-b-0 pb-1 last:pb-0 rounded px-1 -mx-1 ${
                    m.target_element_index != null && hoveredElementIndex === m.target_element_index ? 'bg-indigo-100' : ''
                  }`}
                >
                  <span className="text-gray-500 truncate max-w-[160px]" title={m.target_anchor}>{m.target_anchor}</span>
                  <span>{m.target_value}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Trace Section */}
        <div className="flex-1 p-4 overflow-auto bg-gray-50">
          <div className="text-xs font-semibold text-gray-400 uppercase mb-3">Trace</div>
          {mapped.length === 0 ? (
            <div className="text-sm text-gray-400">Nothing mapped yet.</div>
          ) : (
            <div className="space-y-0 relative">
              <div className="absolute left-[7px] top-2 bottom-2 w-px bg-gray-200" />
              {mapped.map((m, i) => (
                <div
                  key={i}
                  onMouseEnter={() => m.target_element_index != null && setHoveredElement(m.target_element_index)}
                  onMouseLeave={() => m.target_element_index != null && setHoveredElement(null)}
                  className={`relative flex items-start space-x-3 pb-4 last:pb-0 rounded px-1 -mx-1 ${
                    m.target_element_index != null && hoveredElementIndex === m.target_element_index ? 'bg-indigo-100' : ''
                  }`}
                >
                  <div className="w-[15px] h-[15px] rounded-full bg-blue-400 border-[3px] border-gray-50 z-10 mt-1" />
                  <div>
                    <div className="text-sm font-medium text-gray-700">
                      Mapped from <span className="font-mono text-xs">{m.source_anchor}</span>
                    </div>
                    <div className="text-xs text-gray-500">{m.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
