import { useSyncStore } from '../../state/syncStore';

interface BoundingBoxOverlayProps {
  elementId: string;
  /** Relative to the canvas, 0-1 scale — matches AnchorPDF.bbox_relative / DOCX pixel projection. */
  top: number;
  left: number;
  width: number;
  height: number;
}

export function BoundingBoxOverlay({ elementId, top, left, width, height }: BoundingBoxOverlayProps) {
  const activeElementId = useSyncStore((s) => s.activeElementId);
  const setActive = useSyncStore((s) => s.setActive);
  const isActive = activeElementId === elementId;

  return (
    <div
      className={`bbox sync-target${isActive ? ' active' : ''}`}
      style={{
        top: `${top * 100}%`,
        left: `${left * 100}%`,
        width: `${width * 100}%`,
        height: `${height * 100}%`,
      }}
      onMouseEnter={() => setActive(elementId)}
      onMouseLeave={() => setActive(null)}
    />
  );
}
