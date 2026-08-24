import React from 'react';
import { FileCheck2, Download, GitCompare, ExternalLink, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { downloadUrlFor } from '../../api/client';
import type { RollForwardResult } from '../../api/agent';

// Agent-native presentation of a completed roll-forward run.
//
// Phase PROD-UX-1 establishes this surface; nothing populates it yet, because
// this phase runs no roll-forward and mutates no document. What it fixes now is
// the shape of the answer: when a run does return, its output, its magnitude and
// its reconciliation state are stated in the conversation, with the output one
// click away — instead of the user having to know to open the Review pane.

// Keyed by the orchestrator's own reconciliation status. An unrecognised status
// is shown verbatim rather than mapped to something friendlier — the UI must not
// upgrade an unknown outcome into a reassuring one.
const RECONCILIATION_STYLE: Record<string, { label: string; color: string; Icon: typeof ShieldCheck }> = {
  RECONCILED: { label: 'Reconciled', color: 'var(--success)', Icon: ShieldCheck },
  PARTIALLY_RECONCILED: { label: 'Partially reconciled', color: 'var(--warning)', Icon: ShieldAlert },
  NOT_RECONCILED: { label: 'Not reconciled', color: 'var(--error)', Icon: ShieldX },
  NOT_RUN: { label: 'Reconciliation not run', color: 'var(--text-tertiary)', Icon: ShieldAlert },
};

const UNKNOWN_RECONCILIATION = {
  label: 'Reconciliation unknown', color: 'var(--text-tertiary)', Icon: ShieldAlert,
};

const Stat: React.FC<{ label: string; value: number; testId: string }> = ({ label, value, testId }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
    <span data-testid={testId} style={{
      fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2,
    }}>
      {value.toLocaleString()}
    </span>
    <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{label}</span>
  </div>
);

export const RollForwardResultCard: React.FC<{ result: RollForwardResult }> = ({ result }) => {
  const { documents, setActiveDocClientId, setWorkspacePreset } = useWorkspaceStore();
  const reconciliation =
    RECONCILIATION_STYLE[result.reconciliation_status] ?? UNKNOWN_RECONCILIATION;
  const output = result.output_document;

  const openOutput = () => {
    if (!output) return;
    const doc = documents.find((d) => d.docId === output.doc_id);
    if (doc) setActiveDocClientId(doc.clientId);
  };

  const downloadHref = output?.download_url ? downloadUrlFor(output.download_url) : null;

  return (
    <div
      data-testid="roll-forward-result"
      data-reconciliation={result.reconciliation_status}
      style={{
        marginTop: 'var(--space-2)',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderLeft: '3px solid var(--success)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        <FileCheck2 size={14} style={{ color: 'var(--success)', flexShrink: 0 }} />
        <span style={{ flex: 1, fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Roll-forward complete
        </span>
        <span style={{
          display: 'flex', alignItems: 'center', gap: 4,
          fontSize: '10px', fontWeight: 600, color: reconciliation.color,
        }}>
          <reconciliation.Icon size={11} />
          {reconciliation.label}
        </span>
      </div>

      {output && (
        <div style={{
          fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {output.filename}
        </div>
      )}

      <div style={{
        display: 'flex', gap: 'var(--space-4)', padding: 'var(--space-2) 0',
        borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)',
        marginBottom: 'var(--space-2)',
      }}>
        <Stat label="regions changed" value={result.regions_changed} testId="rf-regions-changed" />
        <Stat label="cells updated" value={result.cells_updated} testId="rf-cells-updated" />
        <Stat label="rows inserted" value={result.rows_inserted} testId="rf-rows-inserted" />
      </div>

      {result.reconciliation_detail && (
        <div style={{
          fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.5,
          marginBottom: 'var(--space-2)',
        }}>
          {result.reconciliation_detail}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
        <button
          className="btn btn-primary btn-sm"
          data-testid="rf-open-output"
          onClick={openOutput}
          disabled={!output}
          style={{ fontSize: 'var(--text-xxs)' }}
        >
          <ExternalLink size={11} /> Open Output
        </button>
        <button
          className="btn btn-secondary btn-sm"
          data-testid="rf-review-changes"
          onClick={() => { openOutput(); setWorkspacePreset('review'); }}
          disabled={!result.review_available}
          style={{ fontSize: 'var(--text-xxs)' }}
        >
          <GitCompare size={11} /> Review Changes
        </button>
        {downloadHref && (
          <a
            className="btn btn-ghost btn-sm"
            data-testid="rf-download-docx"
            href={downloadHref}
            download
            style={{ fontSize: 'var(--text-xxs)' }}
          >
            <Download size={11} /> Download DOCX
          </a>
        )}
      </div>
    </div>
  );
};
