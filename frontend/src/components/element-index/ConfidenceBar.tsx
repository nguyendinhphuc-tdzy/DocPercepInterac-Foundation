interface ConfidenceBarProps {
  confidence: number;
}

const LOW_CONFIDENCE_THRESHOLD = 0.8;

export function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const pct = Math.round(confidence * 100);
  const isLow = confidence < LOW_CONFIDENCE_THRESHOLD;

  return (
    <>
      {pct}%
      <span className="confidence-bar">
        <span
          className={`confidence-fill${isLow ? ' low' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </span>
    </>
  );
}
