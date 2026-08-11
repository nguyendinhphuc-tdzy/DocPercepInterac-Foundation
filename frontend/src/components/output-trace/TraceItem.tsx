import type { TraceItemData } from '../../types/element';
import { useSyncStore } from '../../state/syncStore';

interface TraceItemProps {
  item: TraceItemData;
}

export function TraceItem({ item }: TraceItemProps) {
  const activeElementId = useSyncStore((s) => s.activeElementId);
  const setActive = useSyncStore((s) => s.setActive);
  const isActive = item.elementId != null && item.elementId === activeElementId;

  return (
    <div
      className={`trace-item${item.elementId ? ' sync-target' : ''}${isActive ? ' active' : ''}`}
      onMouseEnter={() => item.elementId && setActive(item.elementId)}
      onMouseLeave={() => item.elementId && setActive(null)}
    >
      <div className="trace-time">
        {item.time} - {item.stage}
      </div>
      {item.message}
    </div>
  );
}
