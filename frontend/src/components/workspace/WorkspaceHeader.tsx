import React, { useEffect } from 'react';
import { Undo2, Download, Layout } from 'lucide-react';
import { useWorkspaceStore, type WorkspacePreset } from '../../state/workspaceStore';
import { StatusBadge } from '../shared/StatusBadge';
import { downloadUrlFor } from '../../api/client';

const PRESET_LABELS: Record<WorkspacePreset, string> = {
  agent: 'Agent',
  inspect: 'Inspect',
  review: 'Review',
  compare: 'Compare',
};

export const WorkspaceHeader: React.FC = () => {
  const {
    targetFiles, processingStatus, targetElements, downloadUrl,
    editHistory, isUndoing, undoLastEdit,
    workspacePreset, setWorkspacePreset,
  } = useWorkspaceStore();

  const targetName = targetFiles.length > 0 ? targetFiles[0].name : 'Untitled';
  const canUndo = editHistory.length > 0 && !isUndoing;
  const elementCount = targetElements.length;

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
    switch (processingStatus) {
      case 'idle': return 'idle' as const;
      case 'processing': return 'processing' as const;
      case 'done': return 'ready' as const;
      case 'error': return 'error' as const;
    }
  })();

  const [presetMenuOpen, setPresetMenuOpen] = React.useState(false);

  return (
    <div className="workspace-header">
      <div className="workspace-header-left">
        <span className="workspace-title">Foundation</span>
        <span className="workspace-separator">·</span>
        <span className="workspace-subtitle" title={targetName}>{targetName}</span>
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

        {/* Undo */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={undoLastEdit}
          disabled={!canUndo}
          title={canUndo ? `Undo last edit (${editHistory.length})` : 'No edits to undo'}
        >
          <Undo2 size={13} />
          <span>Undo{editHistory.length > 0 ? ` (${editHistory.length})` : ''}</span>
        </button>

        {/* Download */}
        {downloadUrl && (
          <a
            href={downloadUrlFor(downloadUrl)}
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
