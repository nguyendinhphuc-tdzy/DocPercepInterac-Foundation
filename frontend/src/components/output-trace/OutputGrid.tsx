const EMPTY_COLUMNS = ['A', 'B', 'C'];

/** Pane 4 (left half) — Excel-like preview of the output being written. */
export function OutputGrid() {
  return (
    <div className="excel-grid-wrap">
      <div className="excel-grid">
        <div className="excel-cell excel-header" />
        {EMPTY_COLUMNS.map((col) => (
          <div key={col} className="excel-cell excel-header">
            {col}
          </div>
        ))}
      </div>
      <div className="pane-empty-state" style={{ padding: '24px 12px' }}>
        Chưa có output nào được ghi
      </div>
    </div>
  );
}
