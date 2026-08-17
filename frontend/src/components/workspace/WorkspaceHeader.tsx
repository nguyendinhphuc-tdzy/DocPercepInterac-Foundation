import React, { useEffect } from 'react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { Settings, Command, Activity, FilePlus, Undo2, Loader2, AlertCircle } from 'lucide-react';

const STATUS_DISPLAY = {
  idle: { icon: Activity, color: 'text-gray-400', label: 'No document loaded' },
  processing: { icon: Loader2, color: 'text-blue-600', label: 'Processing', spin: true },
  done: { icon: Activity, color: 'text-green-600', label: 'Ready' },
  error: { icon: AlertCircle, color: 'text-red-600', label: 'Error' },
} as const;

export const WorkspaceHeader: React.FC = () => {
  const { targetFiles, processingStatus, resetWorkspace, editHistory, isUndoing, undoLastEdit } = useWorkspaceStore();

  const targetName = targetFiles.length > 0 ? targetFiles[0].name : 'Untitled';
  const canUndo = editHistory.length > 0 && !isUndoing;
  const status = STATUS_DISPLAY[processingStatus];
  const StatusIcon = status.icon;

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isEditingText = target?.tagName === 'TEXTAREA' || target?.tagName === 'INPUT';
      // Let native undo run inside a field actively being edited — only
      // take over Ctrl/Cmd+Z once the user isn't mid-keystroke in one.
      if (isEditingText) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        undoLastEdit();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [undoLastEdit]);

  return (
    <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 text-sm">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => resetWorkspace()}
          className="text-gray-500 hover:text-gray-900 transition-colors"
          title="New document — clears the current workspace"
        >
          <FilePlus size={16} />
        </button>
        <div className="font-semibold text-gray-900">Foundation</div>
        <div className="text-gray-400">·</div>
        <div className="text-gray-600 truncate max-w-md">{targetName}</div>
      </div>

      <div className="flex items-center space-x-6">
        <button
          onClick={() => undoLastEdit()}
          disabled={!canUndo}
          title={canUndo ? `Undo last edit (${editHistory.length} in this session)` : 'No edits to undo'}
          className={`flex items-center space-x-1.5 px-2 py-1 text-xs rounded border ${
            canUndo
              ? 'text-gray-700 bg-white border-gray-200 hover:bg-gray-50'
              : 'text-gray-300 bg-gray-50 border-gray-100 cursor-not-allowed'
          }`}
        >
          <Undo2 size={13} />
          <span>Undo{editHistory.length > 0 ? ` (${editHistory.length})` : ''}</span>
        </button>

        <div className={`flex items-center space-x-2 ${status.color}`}>
          <StatusIcon size={14} className={'spin' in status && status.spin ? 'animate-spin' : ''} />
          <span className="text-xs font-medium">{status.label}</span>
        </div>

        <button className="flex items-center space-x-2 px-2 py-1 text-xs text-gray-500 bg-white border border-gray-200 rounded hover:bg-gray-50">
          <Command size={12} />
          <span>K</span>
        </button>

        <button className="text-gray-500 hover:text-gray-900">
          <Settings size={16} />
        </button>
      </div>
    </div>
  );
};
