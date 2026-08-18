import React from 'react';
import { FolderOpen, FileText, Clock } from 'lucide-react';
import { useWorkspaceStore } from '../state/workspaceStore';

export const HomePage: React.FC = () => {
  const { setCurrentView, taskHistory } = useWorkspaceStore();

  return (
    <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-app)' }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-8) var(--space-6)' }}>
        {/* Hero */}
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{
            fontSize: 'var(--text-3xl)',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 'var(--space-2)',
          }}>
            Document Intelligence Workspace
          </h1>
          <p style={{
            fontSize: 'var(--text-md)',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            Bring documents into a workspace, then tell Foundation what you need.
          </p>
        </div>

        {/* Primary CTA — opens Workspace directly; documents are added there,
            not through a separate intake page. */}
        <button
          className="btn btn-primary btn-lg"
          onClick={() => setCurrentView('workspace')}
          style={{
            width: '100%',
            justifyContent: 'center',
            padding: 'var(--space-4) var(--space-6)',
            borderRadius: 'var(--radius-xl)',
            fontSize: 'var(--text-lg)',
            marginBottom: 'var(--space-8)',
          }}
        >
          <FolderOpen size={20} />
          <span>Open Workspace</span>
        </button>

        {/* Recent Work */}
        {taskHistory.length > 0 && (
          <div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              marginBottom: 'var(--space-3)',
            }}>
              <Clock size={14} style={{ color: 'var(--text-tertiary)' }} />
              <span style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>Recent work</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {taskHistory.slice(0, 5).map((task) => (
                <button
                  key={task.id}
                  onClick={() => {
                    // Reopening a past task's exact document set isn't implemented yet —
                    // this just returns to the workspace, same as the primary CTA.
                    setCurrentView('workspace');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-4)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%',
                    transition: 'all var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-border)';
                    e.currentTarget.style.background = 'var(--accent-light)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.background = 'var(--bg-surface)';
                  }}
                >
                  <FileText size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {task.name}
                    </div>
                    <div style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-tertiary)',
                    }}>
                      {task.fileCount} files · {task.elementCount} elements · {new Date(task.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
