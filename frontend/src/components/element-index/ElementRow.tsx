import type { ElementRowData } from '../../types/element';
import { useSyncStore } from '../../state/syncStore';
import { ConfidenceBar } from './ConfidenceBar';
import { ReviewBadge } from './ReviewBadge';

const REVIEW_THRESHOLD = 0.8;

interface ElementRowProps {
  element: ElementRowData;
}

export function ElementRow({ element }: ElementRowProps) {
  const elementId = String(element.index);
  const activeElementId = useSyncStore((s) => s.activeElementId);
  const setActive = useSyncStore((s) => s.setActive);
  const isActive = activeElementId === elementId;
  const needsReview =
    element.confidence != null && element.confidence < REVIEW_THRESHOLD;

  return (
    <tr
      className={`sync-target${isActive ? ' active' : ''}`}
      onMouseEnter={() => setActive(elementId)}
      onMouseLeave={() => setActive(null)}
    >
      <td>{elementId}</td>
      <td>
        <span className="element-type-badge">{element.type}</span>
      </td>
      <td>{element.name}</td>
      <td>
        {element.confidence != null && <ConfidenceBar confidence={element.confidence} />}
        {needsReview && <ReviewBadge />}
      </td>
    </tr>
  );
}
