import React, { useMemo, useRef, useState } from 'react';
import { LayoutGrid } from 'lucide-react';
import { EmptyState } from '../../shared/EmptyState';
import { EditableText } from '../../shared/EditableText';
import type { DocumentRendererProps } from './types';

// The XLSX grid keeps Foundation's element anchors (sheet_name +
// cell_address) as its data source, unlike DOCX/PDF — this is a deliberate
// exception, not leftover elements[]-reconstruction debt. Anchors already
// map 1:1 onto real cells with no ambiguity (an element's `text` IS that
// cell's actual value, faithfully extracted by openpyxl — there is no
// lossy "headings only" style reconstruction happening the way the old
// DOCX flow view had). Adopting a full workbook-rendering library
// (FortuneSheet/Univer) was evaluated and deferred: both would need an
// adapter bridging their own internal edit/undo model back into
// Foundation's PATCH contract, real integration risk this phase doesn't
// need given the anchor mapping is already correct. See the phase report
// for the full comparison.
//
// What *was* a real gap — hard truncation at 500 rows / 60 columns with a
// "switch to Elements to see the rest" message — is fixed here via row
// virtualization: only rows near the current scroll position render as
// DOM, but every row remains reachable by scrolling. Columns are rendered
// in full (real workbooks rarely exceed a few dozen), so no column
// virtualization was needed to satisfy "no artificial truncation".
const ROW_HEIGHT = 22;
const OVERSCAN_ROWS = 15;

function parseCellAddress(addr: string): { col: number; row: number } | null {
  const m = /^([A-Za-z]+)(\d+)$/.exec(addr);
  if (!m) return null;
  let col = 0;
  for (const ch of m[1].toUpperCase()) col = col * 26 + (ch.charCodeAt(0) - 64);
  return { col, row: parseInt(m[2], 10) };
}

function colLetter(col: number): string {
  let s = '';
  let n = col;
  while (n > 0) {
    const rem = (n - 1) % 26;
    s = String.fromCharCode(65 + rem) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function cellHighlightStyle(isSelected: boolean, isHighlighted: boolean): React.CSSProperties {
  if (isSelected) return { background: 'var(--accent-light)', boxShadow: 'inset 2px 0 0 var(--accent)' };
  if (isHighlighted) return { background: '#EEF2FF', boxShadow: 'inset 2px 0 0 var(--accent)' };
  return {};
}

export const XlsxRenderer: React.FC<DocumentRendererProps> = ({
  elements, hoveredElementIndex, selectedElementIndex, onHoverElement, onSelectElement, editable, onEditElement,
}) => {
  const sheets = useMemo(() => {
    const bySheet = new Map<string, { el: (typeof elements)[number]; row: number; col: number }[]>();
    for (const el of elements) {
      if (el.anchor.format !== 'xlsx') continue;
      const parsed = parseCellAddress(el.anchor.cell_address);
      if (!parsed) continue;
      const list = bySheet.get(el.anchor.sheet_name) ?? [];
      list.push({ el, ...parsed });
      bySheet.set(el.anchor.sheet_name, list);
    }
    return bySheet;
  }, [elements]);

  const sheetNames = useMemo(() => Array.from(sheets.keys()), [sheets]);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const currentSheet = activeSheet && sheets.has(activeSheet) ? activeSheet : sheetNames[0] ?? null;

  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(600);

  if (sheets.size === 0) {
    return <EmptyState icon={LayoutGrid} title="No spreadsheet cells" description="This document has no XLSX cell data to display as a grid." />;
  }

  const cells = currentSheet ? sheets.get(currentSheet)! : [];
  const maxRow = Math.max(...cells.map((c) => c.row));
  const maxCol = Math.max(...cells.map((c) => c.col));
  const byPosition = new Map(cells.map((c) => [`${c.row},${c.col}`, c.el]));

  const firstVisibleRow = Math.max(1, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN_ROWS);
  const lastVisibleRow = Math.min(maxRow, Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN_ROWS);
  const topSpacerHeight = (firstVisibleRow - 1) * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (maxRow - lastVisibleRow) * ROW_HEIGHT);

  const visibleRowNumbers: number[] = [];
  for (let r = firstVisibleRow; r <= lastVisibleRow; r++) visibleRowNumbers.push(r);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {sheetNames.length > 1 && (
        <div className="sheet-tabs">
          {sheetNames.map((name) => (
            <button
              key={name}
              className={`sheet-tab ${name === currentSheet ? 'active' : ''}`}
              onClick={() => { setActiveSheet(name); setScrollTop(0); scrollRef.current?.scrollTo(0, 0); }}
            >
              {name}
            </button>
          ))}
        </div>
      )}
      <div style={{ padding: 'var(--space-4)', flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {sheetNames.length <= 1 && currentSheet && (
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
            {currentSheet}
          </div>
        )}
        <div
          ref={(node) => {
            scrollRef.current = node;
            if (node) setViewportHeight((prev) => (prev !== node.clientHeight ? node.clientHeight : prev));
          }}
          style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', flex: 1 }}
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        >
          <table
            style={{ borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}
            onMouseOver={(e) => {
              const cell = (e.target as HTMLElement).closest<HTMLElement>('[data-el-index]');
              if (cell) onHoverElement(Number(cell.dataset.elIndex));
            }}
            onMouseOut={(e) => {
              const related = e.relatedTarget as HTMLElement | null;
              if (!related?.closest('[data-el-index]')) onHoverElement(null);
            }}
          >
            <thead>
              <tr>
                <th className="xlsx-grid-corner" />
                {Array.from({ length: maxCol }, (_, i) => (
                  <th key={i} className="xlsx-grid-colhead">{colLetter(i + 1)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {topSpacerHeight > 0 && (
                <tr style={{ height: topSpacerHeight }} aria-hidden="true"><td colSpan={maxCol + 1} /></tr>
              )}
              {visibleRowNumbers.map((r) => (
                <tr key={r} style={{ height: ROW_HEIGHT }}>
                  <th className="xlsx-grid-rowhead">{r}</th>
                  {Array.from({ length: maxCol }, (_, ci) => {
                    const c = ci + 1;
                    const cellEl = byPosition.get(`${r},${c}`);
                    const isHighlighted = !!cellEl && hoveredElementIndex === cellEl.index;
                    const isSelected = !!cellEl && selectedElementIndex === cellEl.index;
                    return (
                      <td
                        key={c}
                        className="xlsx-grid-cell"
                        data-el-index={cellEl ? cellEl.index : undefined}
                        onClick={() => cellEl && onSelectElement(cellEl.index)}
                        style={cellHighlightStyle(isSelected, isHighlighted)}
                      >
                        {cellEl ? (
                          <EditableText
                            value={cellEl.text}
                            onSave={(newValue) => onEditElement(cellEl.index, newValue)}
                            disabled={!editable}
                            className={cellEl.source === 'manual' ? 'bg-amber-50' : ''}
                            title={cellEl.source === 'manual' ? 'Manually edited' : 'Click to edit'}
                          />
                        ) : ''}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {bottomSpacerHeight > 0 && (
                <tr style={{ height: bottomSpacerHeight }} aria-hidden="true"><td colSpan={maxCol + 1} /></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
