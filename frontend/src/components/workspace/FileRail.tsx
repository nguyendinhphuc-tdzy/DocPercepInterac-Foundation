import React, { useRef } from 'react';
import { FileText, File as FileIcon, Sheet, CheckCircle, Loader2, AlertCircle, Plus } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import type { DocumentFormat } from '../../types/element';

// Documents panel owns document intake — the only file input in the app.
// This stays visible regardless of active document/view-mode state, so it
// never depends on the right Document pane's toolbar width.
const ACCEPTED_EXTENSIONS = '.xlsx,.pdf,.docx';

function FileTypeIcon({ format, size = 14 }: { format: DocumentFormat | null; size?: number }) {
  switch (format) {
    case 'xlsx': return <Sheet size={size} style={{ color: '#2E7D32' }} />;
    case 'pdf': return <FileIcon size={size} style={{ color: '#C62828' }} />;
    case 'docx': return <FileText size={size} style={{ color: '#1565C0' }} />;
    default: return <FileIcon size={size} style={{ color: 'var(--text-tertiary)' }} />;
  }
}

function DocStatusIcon({ status }: { status: 'perceiving' | 'ready' | 'error' }) {
  switch (status) {
    case 'ready': return <CheckCircle size={12} style={{ color: 'var(--success)' }} />;
    case 'perceiving': return <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />;
    case 'error': return <AlertCircle size={12} style={{ color: 'var(--error)' }} />;
  }
}

export const FileRail: React.FC = () => {
  const { documents, activeDocClientId, setActiveDocClientId, addDocument, intakeError } = useWorkspaceStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files ?? []).forEach((f) => addDocument(f));
    e.target.value = '';
  };

  return (
    <div className="file-rail">
      <div className="file-rail-header">
        <span className="file-rail-header-title">Documents</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => fileInputRef.current?.click()}
          title="Add documents"
        >
          <Plus size={12} />
          <span>Add</span>
        </button>
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
      {intakeError && (
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
            return (
              <button
                key={doc.clientId}
                className={`file-rail-item ${isActive ? 'active' : ''}`}
                onClick={() => setActiveDocClientId(doc.clientId)}
                title={doc.error ? `${doc.file.name} — ${doc.error}` : doc.file.name}
              >
                <FileTypeIcon format={doc.format} />
                <span className="file-name">{doc.file.name}</span>
                <DocStatusIcon status={doc.status} />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
