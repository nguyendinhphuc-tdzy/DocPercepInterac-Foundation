import { PaneHeader } from '../layout/PaneHeader';
import { ElementRow } from './ElementRow';
import type { ElementRowData } from '../../types/element';

interface ElementIndexTableProps {
  elements?: ElementRowData[];
}

/** Pane 2 — the Element Index (Middle Output), one row per parsed element. */
export function ElementIndexTable({ elements = [] }: ElementIndexTableProps) {
  return (
    <div className="pane">
      <PaneHeader title="Element Index" />
      <div className="pane-content">
        {elements.length === 0 ? (
          <div className="pane-empty-state">Chưa có element nào — chờ tài liệu được parse</div>
        ) : (
          <table className="element-table">
            <thead>
              <tr>
                <th>Anchor ID</th>
                <th>Type</th>
                <th>Text Preview</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {elements.map((element) => (
                <ElementRow key={element.index} element={element} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
