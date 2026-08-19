import React, { useRef, useState } from 'react';
import { FileText, File as FileIcon, Sheet, CheckCircle, Loader2, AlertCircle, Plus, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import type { DocumentFormat } from '../../types/element';

// Documents panel owns document intake — the only file input in the app.
// This stays visible regardless of active document/view-mode state, so it
// never depends on the right Document pane's toolbar width.
const ACCEPTED_EXTENSIONS = '.xlsx,.pdf,.docx';

function FileTypeIcon({ format, size = 14 }: { format: DocumentFormat | null; size?: number }) {
  switch (format) {
    case 'xlsx': return <Sheet size={size} style={{ color: '#2E7D32', flexShrink: 0 }} />;
    case 'pdf': return <FileIcon size={size} style={{ color: '#C62828', flexShrink: 0 }} />;
    case 'docx': return <FileText size={size} style={{ color: '#1565C0', flexShrink: 0 }} />;
    default: return <FileIcon size={size} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />;
  }
}

function DocStatusIcon({ status }: { status: 'perceiving' | 'ready' | 'error' }) {
  switch (status) {
    case 'ready': return <CheckCircle size={12} style={{ color: 'var(--success)', flexShrink: 0 }} />;
    case 'perceiving': return <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)', flexShrink: 0 }} />;
    case 'error': return <AlertCircle size={12} style={{ color: 'var(--error)', flexShrink: 0 }} />;
  }
}

export const FileRail: React.FC = () => {
  const { documents, activeDocClientId, setActiveDocClientId, addDocument, intakeError } = useWorkspaceStore();
  const [collapsed, setCollapsed] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files ?? []).forEach((f) => addDocument(f));
    e.target.value = '';
  };

  return (
    <div className={`file-rail ${collapsed ? 'collapsed' : ''}`} aria-label="Documents collection">
      <div className="file-rail-header">
        {!collapsed && <span className="file-rail-header-title">Documents</span>}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', marginLeft: collapsed ? 'auto' : undefined }}>
          <button
            className="btn btn-secondary btn-sm btn-icon"
            onClick={() => fileInputRef.current?.click()}
            title="Add documents"
            aria-label="Add documents"
          >
            <Plus size={13} />
          </button>
          <button
            className="btn btn-ghost btn-sm btn-icon"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand documents panel' : 'Collapse documents panel'}
            aria-label={collapsed ? 'Expand documents panel' : 'Collapse documents panel'}
          >
            {collapsed ? <PanelLeft size={13} /> : <PanelLeftClose size={13} />}
          </button>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ACCEPTED_EXTENSIONS}
        style={{ display: 'none' }}
        onChange={handleFilesSelected}
        aria-label="Upload documents"
      />
      {intakeError && !collapsed && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2)',
          padding: 'var(--space-2)', margin: 'var(--space-2)',
          background: 'var(--error-light)', border: '1px solid var(--error-border)',
          borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xxs)', color: 'var(--error)',
        }}>
          <AlertCircle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{intakeError}</span>
        </div>
      )}
      {documents.length > 0 && (
        <div className="file-rail-list">
          {documents.map((doc) => {
            const isActive = activeDocClientId === doc.clientId;
            const tooltip = doc.error ? `${doc.file.name} — ${doc.error}` : `${doc.file.name} (${doc.status === 'ready' ? `${doc.elementCount} elements` : doc.status})`;
            return (
              <button
                key={doc.clientId}
                className={`file-rail-item ${isActive ? 'active' : ''} ${collapsed ? 'collapsed' : ''}`}
                onClick={() => setActiveDocClientId(doc.clientId)}
                title={tooltip}
                aria-label={tooltip}
              >
                <FileTypeIcon format={doc.format} />
                {!collapsed && <span className="file-name">{doc.file.name}</span>}
                {!collapsed && <DocStatusIcon status={doc.status} />}
                {collapsed && (
                  <span className={`status-dot ${doc.status}`} />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
