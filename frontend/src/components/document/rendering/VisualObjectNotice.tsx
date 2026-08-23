import React, { useEffect, useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import { fetchVisualObjects, type VisualObjectReport } from '../../../api/workflow';

// An honest status line for a worksheet the renderer cannot draw in full.
//
// openpyxl — the library the perception layer reads workbooks with — exposes
// only pictures and charts out of a sheet's drawing part. Shapes, text boxes,
// connectors, grouped drawings, SmartArt and legacy VML form controls are never
// seen, so they can never be rendered. Rather than presenting a partial sheet as
// if it were whole, this states what is present in the file and not on screen.
//
// Audit only: it renders nothing from the workbook and changes no perception.

export const VisualObjectNotice: React.FC<{
  sessionId: string;
  docId: string;
  sheetName: string | null;
}> = ({ sessionId, docId, sheetName }) => {
  const [report, setReport] = useState<VisualObjectReport | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!sessionId || !docId) return;
    fetchVisualObjects(sessionId, docId)
      .then((result) => { if (!cancelled) setReport(result); })
      .catch(() => { /* the grid itself is unaffected — stay silent */ });
    return () => { cancelled = true; };
  }, [sessionId, docId]);

  if (!report?.applicable || report.fully_rendered !== false) return null;

  const sheet = report.sheets?.find((s) => s.sheet_name === sheetName);
  const scope = sheet && sheet.unrendered_objects > 0 ? sheet.objects : Object.values(report.totals ?? {});
  const missing = scope.filter((o) => o.visibility !== 'RENDERED');
  if (missing.length === 0) return null;

  const summary = missing
    .map((o) => `${o.count} ${o.display_name.toLowerCase()}`)
    .join(', ');

  return (
    <div
      data-testid="xlsx-visual-object-notice"
      data-fully-rendered="false"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        padding: 'var(--space-2) var(--space-3)',
        background: 'var(--warning-light)',
        borderBottom: '1px solid var(--warning-border)',
        fontSize: 'var(--text-xxs)',
        color: 'var(--text-secondary)',
      }}
    >
      <button
        onClick={() => setExpanded((value) => !value)}
        style={{
          display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
          background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
          textAlign: 'left', color: 'var(--warning)', fontWeight: 600,
        }}
      >
        <AlertTriangle size={12} style={{ flexShrink: 0 }} />
        <span style={{ flex: 1 }}>
          {sheet && sheet.unrendered_objects > 0
            ? `This sheet is not shown in full — ${summary} are in the file but not drawn.`
            : `This workbook is not shown in full — ${summary} are in the file but not drawn.`}
        </span>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {expanded && (
        <div style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {missing.map((object) => (
            <div key={object.kind}>
              <strong>{object.display_name} ({object.count})</strong>
              {object.visibility === 'PLACEHOLDER'
                ? ' — shown as a placeholder only. '
                : ' — not detected by the parser. '}
              {object.reason}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
