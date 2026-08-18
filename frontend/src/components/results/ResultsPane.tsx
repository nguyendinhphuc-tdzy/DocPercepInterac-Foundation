import React, { useState } from 'react';
import { CheckCircle, ChevronDown, ChevronRight, Download, FileOutput } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { downloadUrlFor } from '../../api/client';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';
import { EmptyState } from '../shared/EmptyState';

// This pane is the GTPS application's own results view — it only ever
// populates after an explicit GTPS mapping run (components/gpts/), never
// as a side effect of uploading documents. Its GTPS-shaped language here
// is correct: unlike the generic panes, this one IS application-scoped.
export const ResultsPane: React.FC = () => {
  const { documents, gptsMapping, hoveredElementId, setHoveredElement } = useWorkspaceStore();
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const sourceNames = new Map(documents.map((d) => [d.clientId, d.file.name]));
  const targetDoc = documents.find((d) => d.clientId === gptsMapping.targetDocClientId);
  const targetName = targetDoc?.file.name ?? null;
  // `target_element_index` (GTPS's own response shape — untouched) is
  // translated to the canonical `element_id` here, at the point of use,
  // via the target document's already-loaded elements — no GTPS backend
  // change, no second identity system: cross-pane hover still shares one
  // `element_id`-keyed store with every other pane (Foundation Document
  // Perception & Renderer Contract Hardening phase).
  const elementIdForTargetIndex = (targetIndex: number | null): string | null => {
    if (targetIndex == null) return null;
    return targetDoc?.elements?.find((el) => el.index === targetIndex)?.element_id ?? null;
  };
  const hasOutput = gptsMapping.downloadUrl != null;
  const mappedCount = gptsMapping.mapped.length;

  const toggleExpanded = (i: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      return next;
    });
  };

  return (
    <div className="pane-container">
      {/* Header */}
      <div className="pane-header">
        <div className="pane-header-title">
          <FileOutput size={14} />
          <span>GTPS Mapping Output</span>
        </div>
        {hasOutput && gptsMapping.downloadUrl && (
          <a
            href={downloadUrlFor(gptsMapping.downloadUrl)}
            className="btn btn-primary btn-sm"
            style={{ textDecoration: 'none' }}
          >
            <Download size={12} />
            <span>Download</span>
          </a>
        )}
      </div>

      <div className="pane-content" style={{ padding: 0 }}>
        {mappedCount === 0 ? (
          <EmptyState
            icon={FileOutput}
            title="No output yet"
            description={
              gptsMapping.status === 'running'
                ? 'Mapping in progress…'
                : gptsMapping.status === 'idle'
                  ? 'Run GTPS Local File Mapping (Applications menu) to see output here.'
                  : gptsMapping.status === 'done'
                    ? 'No mapping rules matched this document pair.'
                    : (gptsMapping.error ?? 'Mapping failed — try again.')
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
                    {targetName.replace(/\.docx$/, '_patched.docx')}
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
              {gptsMapping.mapped.map((m, i) => {
                const targetElementId = elementIdForTargetIndex(m.target_element_index);
                const isHighlighted = targetElementId != null && hoveredElementId === targetElementId;
                const isExpanded = expanded.has(i);
                const sourceDocName = gptsMapping.sourceDocClientIds
                  .map((id) => sourceNames.get(id))
                  .find(Boolean);
                return (
                  <div
                    key={i}
                    className={`result-card ${isHighlighted ? 'highlighted' : ''}`}
                    onMouseEnter={() => targetElementId != null && setHoveredElement(targetElementId)}
                    onMouseLeave={() => targetElementId != null && setHoveredElement(null)}
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

                    <button
                      className="result-provenance-toggle"
                      onClick={(e) => { e.stopPropagation(); toggleExpanded(i); }}
                    >
                      {isExpanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                      <span>Provenance</span>
                    </button>

                    {isExpanded && (
                      <div className="provenance-chain">
                        <div className="provenance-step">
                          <div>
                            <div className="provenance-step-label">Output</div>
                            <div className="provenance-step-detail">{m.target_value}</div>
                          </div>
                        </div>
                        <div className="provenance-step">
                          <div>
                            <div className="provenance-step-label">Mapped to</div>
                            <div className="provenance-step-detail">{m.target_anchor}{targetName ? ` · ${targetName}` : ''}</div>
                          </div>
                        </div>
                        <div className="provenance-step">
                          <div>
                            <div className="provenance-step-label">Source</div>
                            <div className="provenance-step-detail">
                              {m.source_anchor}{sourceDocName ? ` · ${sourceDocName}` : ''}
                            </div>
                          </div>
                        </div>
                        <div className="provenance-step">
                          <div>
                            <div className="provenance-step-label">Confidence &amp; time</div>
                            <div className="provenance-step-detail">
                              {Math.round(m.confidence * 100)}% · {new Date(m.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
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
