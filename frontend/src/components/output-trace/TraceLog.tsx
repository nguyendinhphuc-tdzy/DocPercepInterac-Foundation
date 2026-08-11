import type { TraceItemData } from '../../types/element';
import { TraceItem } from './TraceItem';

interface TraceLogProps {
  items?: TraceItemData[];
}

/** Pane 4 (right half) — execution timeline, reads from /executions/{id}. */
export function TraceLog({ items = [] }: TraceLogProps) {
  return (
    <div className="trace-log">
      {items.length === 0 ? (
        <div className="pane-empty-state" style={{ padding: 0 }}>
          Chưa có execution log nào
        </div>
      ) : (
        items.map((item) => <TraceItem key={item.id} item={item} />)
      )}
    </div>
  );
}
