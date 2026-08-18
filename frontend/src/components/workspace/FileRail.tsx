import React from 'react';
import { FileText, File as FileIcon, Sheet, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import type { DocumentFormat } from '../../types/element';

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
  const { documents, activeDocClientId, setActiveDocClientId } = useWorkspaceStore();

  if (documents.length === 0) return null;

  return (
    <div className="file-rail">
      <div className="file-rail-header">
        <span className="file-rail-header-title">Documents</span>
        <span style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)' }}>
          {documents.length}
        </span>
      </div>
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
    </div>
  );
};
