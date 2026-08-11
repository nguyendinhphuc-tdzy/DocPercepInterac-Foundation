import { PaneHeader } from '../layout/PaneHeader';
import { OutputGrid } from './OutputGrid';
import { TraceLog } from './TraceLog';

/** Pane 4 — output preview + execution trace, side by side. */
export function OutputTracePane() {
  return (
    <div className="pane">
      <PaneHeader title="Output + Trace" />
      <div className="pane-content">
        <div className="output-container">
          <OutputGrid />
          <TraceLog />
        </div>
      </div>
    </div>
  );
}
