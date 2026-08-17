import React from 'react';
import { FileText, File as FileIcon, Sheet, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';

function getFileExtension(name: string): string {
  return name.split('.').pop()?.toLowerCase() ?? '';
}

function FileTypeIcon({ ext, size = 14 }: { ext: string; size?: number }) {
  switch (ext) {
    case 'xlsx': return <Sheet size={size} style={{ color: '#2E7D32' }} />;
    case 'pdf': return <FileIcon size={size} style={{ color: '#C62828' }} />;
    case 'docx': return <FileText size={size} style={{ color: '#1565C0' }} />;
    default: return <FileIcon size={size} style={{ color: 'var(--text-tertiary)' }} />;
  }
}

function FileStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'done': return <CheckCircle size={12} style={{ color: 'var(--success)' }} />;
    case 'processing': return <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />;
    case 'error': return <AlertCircle size={12} style={{ color: 'var(--error)' }} />;
    default: return null;
  }
}

export const FileRail: React.FC = () => {
  const { sourceFiles, targetFiles, processingStatus, activeFileIndex, setActiveFileIndex } = useWorkspaceStore();

  const allFiles = [
    ...targetFiles.map((f, i) => ({ file: f, role: 'Target' as const, originalIndex: i, globalIndex: i })),
    ...sourceFiles.map((f, i) => ({ file: f, role: 'Source' as const, originalIndex: i, globalIndex: targetFiles.length + i })),
  ];

  if (allFiles.length === 0) return null;

  const fileStatus = processingStatus === 'done' ? 'done' : processingStatus === 'processing' ? 'processing' : 'idle';

  return (
    <div className="file-rail">
      <div className="file-rail-header">
        <span className="file-rail-header-title">Files</span>
        <span style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)' }}>
          {allFiles.length}
        </span>
      </div>
      <div className="file-rail-list">
        {allFiles.map(({ file, role, globalIndex }) => {
          const ext = getFileExtension(file.name);
          const isActive = activeFileIndex === globalIndex;
          return (
            <button
              key={`${role}-${globalIndex}`}
              className={`file-rail-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveFileIndex(globalIndex)}
              title={`${file.name} (${role})`}
            >
              <FileTypeIcon ext={ext} />
              <span className="file-name">{file.name}</span>
              <FileStatusIcon status={fileStatus} />
            </button>
          );
        })}
      </div>
    </div>
  );
};
