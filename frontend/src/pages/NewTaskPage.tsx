import React, { useRef, useState, useCallback } from 'react';
import { Upload, X, ArrowRight, AlertTriangle, Loader2, FileText, File as FileIcon, Sheet } from 'lucide-react';
import { useWorkspaceStore } from '../state/workspaceStore';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileExtension(name: string): string {
  return name.split('.').pop()?.toLowerCase() ?? '';
}

function getFileTypeLabel(ext: string): string {
  switch (ext) {
    case 'xlsx': return 'Source';
    case 'pdf': return 'Source';
    case 'docx': return 'Target';
    default: return 'File';
  }
}

function FileTypeIcon({ ext }: { ext: string }) {
  switch (ext) {
    case 'xlsx': return <Sheet size={16} />;
    case 'pdf': return <FileIcon size={16} />;
    case 'docx': return <FileText size={16} />;
    default: return <FileIcon size={16} />;
  }
}

export const NewTaskPage: React.FC = () => {
  const {
    sourceFiles, targetFiles, intakeError, processingStatus, processingError,
    addDocument, removeSourceFile, removeTargetFile, runProcessing,
  } = useWorkspaceStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const allFiles = [
    ...targetFiles.map((f, i) => ({ file: f, type: 'target' as const, index: i })),
    ...sourceFiles.map((f, i) => ({ file: f, type: 'source' as const, index: i })),
  ];
  const totalFiles = sourceFiles.length + targetFiles.length;
  const isReady = sourceFiles.length > 0 && targetFiles.length > 0;
  const isProcessing = processingStatus === 'processing';

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
          What would you like to work with?
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
        {(intakeError || (processingStatus === 'error' && processingError)) && (
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
            <span>{intakeError ?? processingError}</span>
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
              }}>Files</span>
              <span style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-tertiary)',
              }}>{totalFiles} / 10</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {allFiles.map(({ file, type, index }) => {
                const ext = getFileExtension(file.name);
                return (
                  <div key={`${type}-${index}`} className="file-row">
                    <div className={`file-icon ${ext}`}>
                      <FileTypeIcon ext={ext} />
                    </div>
                    <div className="file-info">
                      <div className="file-name">{file.name}</div>
                      <div className="file-meta">
                        {getFileTypeLabel(ext)} · {formatFileSize(file.size)}
                      </div>
                    </div>
                    <button
                      className="file-remove"
                      onClick={() => type === 'source' ? removeSourceFile(index) : removeTargetFile(index)}
                      title="Remove file"
                      aria-label={`Remove ${file.name}`}
                    >
                      <X size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Analyze Button */}
        {totalFiles > 0 && (
          <button
            className={`btn ${isReady ? 'btn-primary' : 'btn-secondary'} btn-lg`}
            onClick={() => isReady && runProcessing()}
            disabled={!isReady || isProcessing}
            style={{
              width: '100%',
              justifyContent: 'center',
              marginTop: 'var(--space-4)',
              borderRadius: 'var(--radius-xl)',
            }}
          >
            {isProcessing ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Processing…</span>
              </>
            ) : isReady ? (
              <>
                <span>Analyze Documents</span>
                <ArrowRight size={16} />
              </>
            ) : (
              <span>
                Add a {targetFiles.length === 0 ? 'target document (.docx)' : 'source file (.xlsx/.pdf)'} to continue
              </span>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
