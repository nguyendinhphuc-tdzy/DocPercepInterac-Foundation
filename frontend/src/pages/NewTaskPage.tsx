import React, { useRef, useState, useCallback } from 'react';
import { Upload, X, ArrowRight, AlertTriangle, Loader2, FileText, File as FileIcon, Sheet } from 'lucide-react';
import { useWorkspaceStore } from '../state/workspaceStore';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileTypeIcon({ format }: { format: string | null }) {
  switch (format) {
    case 'xlsx': return <Sheet size={16} />;
    case 'pdf': return <FileIcon size={16} />;
    case 'docx': return <FileText size={16} />;
    default: return <FileIcon size={16} />;
  }
}

export const NewTaskPage: React.FC = () => {
  const {
    documents, intakeError, addDocument, removeDocument, setCurrentView,
  } = useWorkspaceStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const totalFiles = documents.length;
  const isPerceiving = documents.some((d) => d.status === 'perceiving');
  const hasReadyDocument = documents.some((d) => d.status === 'ready');

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    Array.from(e.dataTransfer.files).forEach(f => addDocument(f));
  }, [addDocument]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  return (
    <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-app)' }}>
      <div style={{ maxWidth: 560, margin: '0 auto', padding: 'var(--space-8) var(--space-6)' }}>
        {/* Title */}
        <h1 style={{
          fontSize: 'var(--text-2xl)',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: 'var(--space-1)',
          textAlign: 'center',
        }}>
          New Document Task
        </h1>
        <p style={{
          fontSize: 'var(--text-base)',
          color: 'var(--text-secondary)',
          textAlign: 'center',
          marginBottom: 'var(--space-6)',
        }}>
          Add documents to get started — Foundation reads them right away.
        </p>

        {/* Drop Zone */}
        <div
          className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragOver(false)}
          role="button"
          tabIndex={0}
          aria-label="Upload files"
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
        >
          <div className="drop-icon">
            <Upload size={22} />
          </div>
          <div className="drop-title">Drop files here</div>
          <div className="drop-subtitle">or click to browse</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
            PDF · XLSX · DOCX
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".xlsx,.pdf,.docx"
            style={{ display: 'none' }}
            onChange={(e) => {
              Array.from(e.target.files ?? []).forEach(f => addDocument(f));
              e.target.value = '';
            }}
          />
        </div>

        {/* Error */}
        {intakeError && (
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--space-2)',
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'var(--error-light)',
            border: '1px solid var(--error-border)',
            borderRadius: 'var(--radius-lg)',
            fontSize: 'var(--text-sm)',
            color: 'var(--error)',
          }}>
            <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{intakeError}</span>
          </div>
        )}

        {/* File List */}
        {totalFiles > 0 && (
          <div style={{ marginTop: 'var(--space-4)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-2)',
            }}>
              <span style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>Documents</span>
              <span style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-tertiary)',
              }}>{totalFiles}</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {documents.map((doc) => (
                <div key={doc.clientId} className="file-row">
                  <div className={`file-icon ${doc.format ?? ''}`}>
                    <FileTypeIcon format={doc.format} />
                  </div>
                  <div className="file-info">
                    <div className="file-name">{doc.file.name}</div>
                    <div className="file-meta">
                      {doc.status === 'perceiving' && 'Reading…'}
                      {doc.status === 'ready' && `${doc.elementCount} elements · ${formatFileSize(doc.file.size)}`}
                      {doc.status === 'error' && (doc.error ?? 'Failed to read')}
                    </div>
                  </div>
                  <button
                    className="file-remove"
                    onClick={() => removeDocument(doc.clientId)}
                    title="Remove file"
                    aria-label={`Remove ${doc.file.name}`}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Continue — Perceive already ran automatically per document above;
            this just moves to the workspace to view/inspect/edit them. Any
            further task (e.g. GTPS mapping) is a separate, explicit
            application action inside the workspace, not gated here. */}
        {totalFiles > 0 && (
          <button
            className={`btn ${hasReadyDocument ? 'btn-primary' : 'btn-secondary'} btn-lg`}
            onClick={() => hasReadyDocument && setCurrentView('workspace')}
            disabled={!hasReadyDocument}
            style={{
              width: '100%',
              justifyContent: 'center',
              marginTop: 'var(--space-4)',
              borderRadius: 'var(--radius-xl)',
            }}
          >
            {isPerceiving && !hasReadyDocument ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Reading documents…</span>
              </>
            ) : (
              <>
                <span>Open Workspace</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
