import React, { useEffect } from 'react';
import { Undo2, Download, Layout, LayoutGrid } from 'lucide-react';
import { useWorkspaceStore, type WorkspacePreset } from '../../state/workspaceStore';
import { StatusBadge } from '../shared/StatusBadge';
import { downloadUrlFor } from '../../api/client';
import { GptsMappingAction } from '../gpts/GptsMappingAction';

const PRESET_LABELS: Record<WorkspacePreset, string> = {
  agent: 'Agent',
  inspect: 'Inspect',
  review: 'Review',
  compare: 'Compare',
};

export const WorkspaceHeader: React.FC = () => {
  const {
    documents, activeDocClientId, downloadUrlForActiveDoc,
    editHistory, isUndoing, undoLastEdit,
    workspacePreset, setWorkspacePreset,
  } = useWorkspaceStoreExtras();

  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? null;
  const docName = activeDoc?.file.name ?? 'No document selected';
  const canUndo = editHistory.length > 0 && !isUndoing;
  const elementCount = activeDoc?.elementCount ?? 0;

  // Global Ctrl/Cmd+Z undo
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isEditingText = target?.tagName === 'TEXTAREA' || target?.tagName === 'INPUT';
      if (isEditingText) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        undoLastEdit();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [undoLastEdit]);

  const statusType = (() => {
    switch (activeDoc?.status) {
      case undefined: return 'idle' as const;
      case 'perceiving': return 'processing' as const;
      case 'ready': return 'ready' as const;
      case 'error': return 'error' as const;
    }
  })();

  const [presetMenuOpen, setPresetMenuOpen] = React.useState(false);
  const [appsMenuOpen, setAppsMenuOpen] = React.useState(false);

  return (
    <div className="workspace-header">
      <div className="workspace-header-left">
        <span className="workspace-title">Foundation</span>
        <span className="workspace-separator">·</span>
        <span className="workspace-subtitle" title={docName}>{docName}</span>
        <StatusBadge status={statusType} />
        {elementCount > 0 && (
          <span style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-tertiary)',
          }}>
            {elementCount.toLocaleString()} elements
          </span>
        )}
      </div>

      <div className="workspace-header-right">
        {/* Applications — secondary, opt-in application entry points. GTPS
            mapping lives here, not as a default workspace action, so
            uploading documents never implies running it. */}
        <div style={{ position: 'relative' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setAppsMenuOpen(!appsMenuOpen)}
            title="Application actions"
          >
            <LayoutGrid size={13} />
            <span>Applications</span>
          </button>
          {appsMenuOpen && <GptsMappingAction onClose={() => setAppsMenuOpen(false)} />}
        </div>

        {/* Workspace preset selector */}
        <div style={{ position: 'relative' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPresetMenuOpen(!presetMenuOpen)}
            title="Change workspace layout"
          >
            <Layout size={13} />
            <span>{PRESET_LABELS[workspacePreset]}</span>
          </button>
          {presetMenuOpen && (
            <>
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 40 }}
                onClick={() => setPresetMenuOpen(false)}
              />
              <div style={{
                position: 'absolute',
                right: 0,
                top: '100%',
                marginTop: 4,
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-lg)',
                padding: 'var(--space-1)',
                zIndex: 50,
                minWidth: 160,
              }}>
                <div style={{
                  padding: 'var(--space-2) var(--space-3)',
                  fontSize: 'var(--text-xxs)',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}>Workspace</div>
                {(Object.keys(PRESET_LABELS) as WorkspacePreset[]).map((preset) => (
                  <button
                    key={preset}
                    onClick={() => { setWorkspacePreset(preset); setPresetMenuOpen(false); }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-2)',
                      width: '100%',
                      padding: 'var(--space-2) var(--space-3)',
                      background: 'none',
                      border: 'none',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontSize: 'var(--text-sm)',
                      color: workspacePreset === preset ? 'var(--accent)' : 'var(--text-primary)',
                      fontWeight: workspacePreset === preset ? 600 : 400,
                      textAlign: 'left',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-hover)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
                  >
                    <span style={{
                      width: 14,
                      fontSize: 'var(--text-xs)',
                    }}>{workspacePreset === preset ? '●' : '○'}</span>
                    <span>{PRESET_LABELS[preset]}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Undo — undoes the active document's last edit */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={undoLastEdit}
          disabled={!canUndo}
          title={canUndo ? `Undo last edit (${editHistory.length})` : 'No edits to undo'}
        >
          <Undo2 size={13} />
          <span>Undo{editHistory.length > 0 ? ` (${editHistory.length})` : ''}</span>
        </button>

        {/* Download — the active document's own patched output, if any
            (works whether the patch came from a manual edit or a GTPS
            mapping run: both write to the same generic per-document
            download endpoint). */}
        {downloadUrlForActiveDoc && (
          <a
            href={downloadUrlFor(downloadUrlForActiveDoc)}
            className="btn btn-primary btn-sm"
            style={{ textDecoration: 'none' }}
          >
            <Download size={13} />
            <span>Download</span>
          </a>
        )}
      </div>
    </div>
  );
};

// Small convenience wrapper: derives the active document's download URL
// (available once it has a docId — the generic download route resolves
// whether a patch actually exists) from store fields, without adding a
// dedicated store field just for this header.
function useWorkspaceStoreExtras() {
  const state = useWorkspaceStore();
  const activeDoc = state.documents.find((d) => d.clientId === state.activeDocClientId) ?? null;
  const downloadUrlForActiveDoc = activeDoc?.docId && activeDoc.hasPatch && state.sessionId
    ? `/api/documents/${state.sessionId}/download/${activeDoc.docId}`
    : null;
  return { ...state, downloadUrlForActiveDoc };
}
