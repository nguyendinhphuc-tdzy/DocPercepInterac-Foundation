import type { ReactNode } from 'react';

interface DocumentCanvasProps {
  children?: ReactNode;
}

/** Renders the page surface for Pane 1. With no document loaded, shows an empty state. */
export function DocumentCanvas({ children }: DocumentCanvasProps) {
  if (!children) {
    return (
      <div className="pane-empty-state">
        <svg
          className="empty-icon"
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>Chưa có tài liệu nào được tải lên</span>
      </div>
    );
  }

  return <div className="doc-canvas">{children}</div>;
}
