import { PaneHeader } from '../layout/PaneHeader';
import { DocumentCanvas } from './DocumentCanvas';

/** Pane 1 — renders the source document page + bounding boxes from Anchor data. */
export function InputViewer() {
  return (
    <div className="pane">
      <PaneHeader title="Input Viewer" />
      <div className="pane-content" style={{ background: '#e2e8f0' }}>
        <DocumentCanvas />
      </div>
    </div>
  );
}
