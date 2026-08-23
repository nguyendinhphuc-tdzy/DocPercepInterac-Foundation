import React from 'react';
import { FolderOpen, FileText, Clock, ArrowRight, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../state/workspaceStore';
import { useWorkflowStore } from '../state/workflowStore';

export const HomePage: React.FC = () => {
  const { setCurrentView, startWorkflow, exitWorkflow, taskHistory } = useWorkspaceStore();
  const resetWorkflow = useWorkflowStore((s) => s.reset);

  // A workflow starter opens the workflow's own structured intake, not the
  // generic workspace: the user is asked for named inputs instead of being left
  // to work out what the workflow needs.
  const beginRollForward = () => {
    resetWorkflow();
    startWorkflow('LOCAL_FILE_ROLL_FORWARD');
  };

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

        {/* Workflow starters — a named workflow with a structured intake. */}
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{
            fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-tertiary)',
            textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--space-3)',
          }}>
            Start a workflow
          </div>

          <div
            data-testid="workflow-starter-LOCAL_FILE_ROLL_FORWARD"
            style={{
              display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)',
              padding: 'var(--space-4)', background: 'var(--bg-surface)',
              border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
            }}
          >
            <div style={{
              width: 34, height: 34, borderRadius: 'var(--radius-lg)', flexShrink: 0,
              background: 'var(--accent-light)', border: '1px solid var(--accent-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <RefreshCw size={16} style={{ color: 'var(--accent)' }} />
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)',
                marginBottom: 2,
              }}>
                Local File Roll-Forward
              </div>
              <p style={{
                fontSize: 'var(--text-sm)', color: 'var(--text-secondary)',
                lineHeight: 1.6, marginBottom: 'var(--space-3)',
              }}>
                Update last year's Local File using current-year financial, tax and
                supporting source data.
              </p>
              <button
                className="btn btn-primary"
                data-testid="start-workflow-LOCAL_FILE_ROLL_FORWARD"
                onClick={beginRollForward}
              >
                <span>Start Workflow</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </div>

        {/* Generic entry — opens Workspace directly; documents are added there,
            not through a separate intake page. */}
        <button
          className="btn btn-primary btn-lg"
          onClick={() => {
            // The generic workspace is not a workflow — leaving workflow mode
            // here keeps the two entry points from bleeding into each other.
            exitWorkflow();
            setCurrentView('workspace');
          }}
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
