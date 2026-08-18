import React, { useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';

// The GTPS application's own entry point — physically isolated under
// components/gpts/, mirroring foundation/applications/gpts/. Deliberately
// NOT surfaced as a default/prominent workspace CTA (see WorkspaceHeader's
// secondary "Applications" menu, which is the only place this renders):
// role assignment (source vs. target) only ever happens here, as an
// explicit, opt-in action — never automatically from uploading documents.
export const GptsMappingAction: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const { documents, gptsMapping, runGptsMappingTask } = useWorkspaceStore();
  const readyDocs = documents.filter((d) => d.status === 'ready');

  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [targetId, setTargetId] = useState<string | null>(null);

  const isRunning = gptsMapping.status === 'running';
  const canRun = sourceIds.length > 0 && targetId !== null && !isRunning;

  const toggleSource = (clientId: string) => {
    setSourceIds((prev) => prev.includes(clientId)
      ? prev.filter((id) => id !== clientId)
      : [...prev, clientId]);
  };

  return (
    <div style={{
      position: 'absolute', right: 0, top: '100%', marginTop: 4,
      background: 'var(--bg-surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
      padding: 'var(--space-4)', zIndex: 50, width: 320,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
        <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>GTPS Local File Mapping</span>
        <button className="btn btn-secondary btn-sm" onClick={onClose} aria-label="Close" title="Close">
          <X size={13} />
        </button>
      </div>

      {readyDocs.length === 0 ? (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
          Add and perceive documents first, then pick which ones to map here.
        </p>
      ) : (
        <>
          <div style={{ marginBottom: 'var(--space-3)' }}>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 'var(--space-1)' }}>
              Source document(s)
            </div>
            {readyDocs.map((doc) => (
              <label key={doc.clientId} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--text-sm)', padding: '2px 0' }}>
                <input
                  type="checkbox"
                  checked={sourceIds.includes(doc.clientId)}
                  disabled={doc.clientId === targetId}
                  onChange={() => toggleSource(doc.clientId)}
                />
                {doc.file.name}
              </label>
            ))}
          </div>

          <div style={{ marginBottom: 'var(--space-3)' }}>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 'var(--space-1)' }}>
              Target document
            </div>
            {readyDocs.map((doc) => (
              <label key={doc.clientId} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--text-sm)', padding: '2px 0' }}>
                <input
                  type="radio"
                  name="gpts-target"
                  checked={targetId === doc.clientId}
                  disabled={sourceIds.includes(doc.clientId)}
                  onChange={() => setTargetId(doc.clientId)}
                />
                {doc.file.name}
              </label>
            ))}
          </div>

          <button
            className="btn btn-primary btn-sm"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!canRun}
            onClick={() => targetId && runGptsMappingTask(sourceIds, targetId)}
          >
            {isRunning ? <Loader2 size={13} className="animate-spin" /> : null}
            <span>{isRunning ? 'Running…' : 'Run Mapping'}</span>
          </button>

          {gptsMapping.status === 'error' && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--error)', marginTop: 'var(--space-2)' }}>
              {gptsMapping.error}
            </p>
          )}
          {gptsMapping.status === 'done' && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--success)', marginTop: 'var(--space-2)' }}>
              Done — {gptsMapping.mapped.length} elements mapped. See the Output pane.
            </p>
          )}
        </>
      )}
    </div>
  );
};
