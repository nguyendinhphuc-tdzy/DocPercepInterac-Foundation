import React from 'react';
import { CheckCircle, Download, FileOutput } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { downloadUrlFor } from '../../api/client';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';
import { EmptyState } from '../shared/EmptyState';

export const ResultsPane: React.FC = () => {
  const { mapped, downloadUrl, processingStatus, targetFiles, hoveredElementIndex, setHoveredElement } = useWorkspaceStore();

  const targetName = targetFiles.length > 0 ? targetFiles[0].name : null;
  const hasOutput = downloadUrl != null;
  const mappedCount = mapped.length;

  return (
    <div className="pane-container">
      {/* Header */}
      <div className="pane-header">
        <div className="pane-header-title">
          <FileOutput size={14} />
          <span>Output</span>
        </div>
        {hasOutput && (
          <a
            href={downloadUrlFor(downloadUrl)}
            className="btn btn-primary btn-sm"
            style={{ textDecoration: 'none' }}
          >
            <Download size={12} />
            <span>Download DOCX</span>
          </a>
        )}
      </div>

      <div className="pane-content" style={{ padding: 0 }}>
        {mappedCount === 0 ? (
          <EmptyState
            icon={FileOutput}
            title="No output yet"
            description={
              processingStatus === 'processing'
                ? 'Mapping in progress…'
                : processingStatus === 'idle'
                  ? 'Upload and analyze documents to generate output.'
                  : processingStatus === 'done'
                    ? 'No mapping rules matched this document pair.'
                    : 'Processing failed — check the error above.'
            }
          />
        ) : (
          <div style={{ padding: 'var(--space-3)' }}>
            {/* Output Summary */}
            {hasOutput && (
              <div style={{
                padding: 'var(--space-3) var(--space-4)',
                background: 'var(--success-light)',
                border: '1px solid var(--success-border)',
                borderRadius: 'var(--radius-lg)',
                marginBottom: 'var(--space-4)',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-2)',
                  marginBottom: 'var(--space-2)',
                }}>
                  <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                  <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                    Output Ready
                  </span>
                </div>
                {targetName && (
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-1)' }}>
                    {targetName.replace('.docx', '_patched.docx')}
                  </div>
                )}
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                  {mappedCount} elements updated
                </div>
              </div>
            )}

            {/* Results header */}
            <div style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginBottom: 'var(--space-2)',
            }}>
              Mapped Values · {mappedCount}
            </div>

            {/* Result Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {mapped.map((m, i) => {
                const isHighlighted = m.target_element_index != null && hoveredElementIndex === m.target_element_index;
                return (
                  <div
                    key={i}
                    className={`result-card ${isHighlighted ? 'highlighted' : ''}`}
                    onMouseEnter={() => m.target_element_index != null && setHoveredElement(m.target_element_index)}
                    onMouseLeave={() => m.target_element_index != null && setHoveredElement(null)}
                  >
                    <div className="result-source" title={m.source_anchor}>
                      {m.target_anchor}
                    </div>
                    <div className="result-value">{m.target_value}</div>
                    <div className="result-meta">
                      <ConfidenceBadge confidence={m.confidence} />
                      <span style={{
                        fontSize: 'var(--text-xxs)',
                        color: 'var(--text-tertiary)',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        ← {m.source_anchor}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
