import type { AnchorDOCX, ElementRowData } from '../../../types/element';
import { idOf } from '../../../utils/elementId';
import type { MappingReport, MappingStatus } from './types';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

export interface DocxElementMap {
  // element_id -> the specific rendered DOM node representing it (a
  // paragraph/heading/image node, or one table cell's node). Only holds
  // entries for elements whose status is "available" — callers must check
  // `statusByElementId` before assuming a lookup here will succeed.
  nodeByElementId: Map<string, HTMLElement>;
  // Per-element outcome — the actual identity contract of this phase.
  // NEVER a single document-level boolean: one paragraph/image/table
  // failing to resolve must never disable the others (failure isolation).
  statusByElementId: Map<string, MappingStatus>;
  report: MappingReport;
}

// docx-preview (github.com/VolodymyrBaydalka/docxjs) exposes no built-in
// mapping from its rendered HTML back to source identity — confirmed by
// inspecting its docs/API before choosing this strategy. It gives us three
// independent signals to resolve identity from CONTENT rather than
// position, one per object category:
//
//   Text (heading/paragraph): exact rendered TEXT CONTENT, disambiguated
//   by occurrence ordinal among nodes/elements sharing that exact text —
//   mirrors the backend's own `duplicate_ordinal` disambiguation strategy
//   (perception/anchor_builder.py) for the same "repeated boilerplate"
//   problem. A single dropped/merged paragraph in the rendered DOM only
//   affects elements whose text+ordinal collide with it; every other text
//   element still resolves independently.
//
//   Images: BYTE CONTENT via the media manifest. `useBase64URL: true`
//   makes docx-preview embed each picture as a `data:...;base64,...` URI
//   directly in the rendered <img>'s src — comparing that base64 payload
//   against each media asset's own bytes (fetched from the media
//   endpoint) identifies which Foundation IMAGE element a given <img> tag
//   actually is, by real content, with zero dependency on DOM/array order.
//
//   Tables: table_hash — the SAME sha256(header-row-text)[:8] the backend
//   already computes (perception/anchor_builder.py::build_table_hash) —
//   recomputed here from each rendered <table>'s own first row and matched
//   against the anchor's recorded hash. A table that moved or whose
//   position no longer matches document order still resolves correctly;
//   only a table whose header row text actually changed becomes
//   unavailable, independently of every other table.
//
// If a given signal genuinely can't establish an object's identity (e.g.
// an element's text doesn't appear anywhere in the rendered DOM at all),
// that ONE element is marked "unavailable" — the document keeps rendering
// and every other resolvable element stays fully interactive.
export async function buildDocxElementMap(
  container: HTMLElement,
  elements: ElementRowData[],
  fetchMediaBytes: (mediaId: string) => Promise<ArrayBuffer | null>,
): Promise<DocxElementMap> {
  const nodeByElementId = new Map<string, HTMLElement>();
  const statusByElementId = new Map<string, MappingStatus>();

  mapTextFlowElements(container, elements, nodeByElementId, statusByElementId);
  await mapTableCells(container, elements, nodeByElementId, statusByElementId);
  await mapImages(container, elements, nodeByElementId, statusByElementId, fetchMediaBytes);
  markUnmappableAsUnavailable(elements, statusByElementId);

  const report = buildReport(elements, statusByElementId);
  return { nodeByElementId, statusByElementId, report };
}

function markUnmappableAsUnavailable(elements: ElementRowData[], statusByElementId: Map<string, MappingStatus>) {
  // Anything not attempted above (chart/drawing/header/footer/footnote/
  // endnote/comment/annotation) has no DOM region this phase maps to —
  // matches its own honest `capabilities.selectable=false` from the
  // backend (perception/element_classifier.py). Recorded explicitly as
  // "unavailable" rather than left out of the report entirely, so the
  // coverage summary reflects the whole document, not just the subset
  // this mapper attempts.
  for (const el of elements) {
    const id = idOf(el);
    if (!statusByElementId.has(id)) statusByElementId.set(id, 'unavailable');
  }
}

function buildReport(elements: ElementRowData[], statusByElementId: Map<string, MappingStatus>): MappingReport {
  const byStatus: MappingReport['byStatus'] = { available: 0, partial: 0, unavailable: 0, ambiguous: 0 };
  const byType: MappingReport['byType'] = {};
  for (const el of elements) {
    const status = statusByElementId.get(idOf(el)) ?? 'unavailable';
    byStatus[status] += 1;
    const t = byType[el.type] ?? { total: 0, available: 0 };
    t.total += 1;
    if (status === 'available') t.available += 1;
    byType[el.type] = t;
  }
  return { total: elements.length, byStatus, byType };
}

// ── Text (heading/paragraph): exact-text + occurrence-ordinal ──────────────

function mapTextFlowElements(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
) {
  const textFlowElements = elements.filter((el) => el.type === 'heading' || el.type === 'para');
  if (textFlowElements.length === 0) return;

  const renderedNodes = Array.from(
    container.querySelectorAll<HTMLElement>('p, h1, h2, h3, h4, h5, h6')
  ).filter((node) => !node.closest('table') && node.querySelector('img') == null && (node.textContent ?? '').trim().length > 0);

  // Ordered occurrence lists, keyed by exact trimmed text — one list per
  // distinct string, in document order, on BOTH sides.
  const renderedByText = new Map<string, HTMLElement[]>();
  for (const node of renderedNodes) {
    const text = (node.textContent ?? '').trim();
    const list = renderedByText.get(text) ?? [];
    list.push(node);
    renderedByText.set(text, list);
  }

  const seenOrdinal = new Map<string, number>();
  for (const el of textFlowElements) {
    const id = idOf(el);
    const text = el.text.trim();
    if (!text) {
      // An empty heading/paragraph has no content signal to match by at
      // all — genuinely unavailable, not a bug in the matching strategy.
      statusByElementId.set(id, 'unavailable');
      continue;
    }
    const ordinal = seenOrdinal.get(text) ?? 0;
    seenOrdinal.set(text, ordinal + 1);

    const candidates = renderedByText.get(text);
    const node = candidates?.[ordinal];
    if (node) {
      nodeByElementId.set(id, node);
      // "ambiguous" (not "available") when this exact text repeats more
      // often on one side than we can be fully certain corresponds 1:1 on
      // the other — still interactive (best candidate is used), but the
      // caller can distinguish full confidence from a repeated-boilerplate
      // best-effort match.
      const totalRendered = candidates?.length ?? 0;
      const totalFoundation = textFlowElements.filter((e) => e.text.trim() === text).length;
      statusByElementId.set(id, totalRendered === totalFoundation ? 'available' : 'ambiguous');
    } else {
      statusByElementId.set(id, 'unavailable');
    }
  }
}

// ── Tables: table_hash content match, independent per table ────────────────

async function sha256Hex8(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hex = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
  return hex.slice(0, 8);
}

async function mapTableCells(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
): Promise<void> {
  const tableGroups = new Map<number, ElementRowData[]>();
  for (const el of elements) {
    if (el.type === 'cell' && isDocxAnchor(el.anchor) && el.anchor.table_index !== null && el.anchor.table_index !== undefined) {
      const list = tableGroups.get(el.anchor.table_index) ?? [];
      list.push(el);
      tableGroups.set(el.anchor.table_index, list);
    }
  }
  if (tableGroups.size === 0) return;

  const renderedTables = Array.from(container.querySelectorAll<HTMLTableElement>('table'));
  // sha256(header-row-text)[:8] is async (Web Crypto) but there are
  // typically few tables per document — computing all hashes up front,
  // then matching each Foundation table by hash rather than position, is
  // simple and keeps every table's resolution independent of the others.
  const hashed = await Promise.all(renderedTables.map(async (table) => {
    const firstRow = table.querySelector('tr');
    const headerText = firstRow
      ? Array.from(firstRow.querySelectorAll('td, th')).map((c) => (c.textContent ?? '').trim()).join('')
      : '';
    return { table, hash: await sha256Hex8(headerText) };
  }));
  const tableByHash = new Map<string, HTMLTableElement>();
  for (const { table, hash } of hashed) if (!tableByHash.has(hash)) tableByHash.set(hash, table);

  for (const [, cells] of tableGroups) {
    const expectedHash = cells.find((c) => isDocxAnchor(c.anchor))?.anchor;
    const tableHash = expectedHash && isDocxAnchor(expectedHash) ? expectedHash.table_hash : null;
    const tableNode = tableHash ? tableByHash.get(tableHash) : undefined;

    if (!tableNode) {
      for (const cell of cells) statusByElementId.set(idOf(cell), 'unavailable');
      continue;
    }
    const rows = Array.from(tableNode.querySelectorAll<HTMLTableRowElement>('tr'));
    for (const cell of cells) {
      if (!isDocxAnchor(cell.anchor)) continue;
      const r = cell.anchor.row_index ?? 0;
      const c = cell.anchor.col_index ?? 0;
      const row = rows[r];
      const cellNode = row?.querySelectorAll<HTMLElement>('td, th')[c];
      const id = idOf(cell);
      if (cellNode) {
        nodeByElementId.set(id, cellNode);
        statusByElementId.set(id, 'available');
      } else {
        statusByElementId.set(id, 'partial'); // table identity resolved; this specific row/col didn't
      }
    }
  }
}

// ── Images: byte-content match via the media manifest ──────────────────────

function bufferToBase64(buf: ArrayBuffer): string {
  let binary = '';
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

async function mapImages(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
  fetchMediaBytes: (mediaId: string) => Promise<ArrayBuffer | null>,
) {
  const imageElements = elements.filter((el) => el.type === 'image' && isDocxAnchor(el.anchor));
  if (imageElements.length === 0) return;

  const renderedImages = Array.from(container.querySelectorAll<HTMLImageElement>('img')).filter((img) => !img.closest('table'));
  // Extract each rendered <img>'s base64 payload once, up front — O(images)
  // rather than re-parsing on every comparison.
  const renderedPayloads = renderedImages.map((img) => {
    const m = /^data:[^;]+;base64,(.+)$/.exec(img.src);
    return { img, base64: m ? m[1] : null };
  });

  await Promise.all(imageElements.map(async (el) => {
    const id = idOf(el);
    const mediaId = isDocxAnchor(el.anchor) ? el.anchor.media_id : null;
    if (!mediaId) {
      statusByElementId.set(id, 'unavailable');
      return;
    }
    const bytes = await fetchMediaBytes(mediaId);
    if (!bytes) {
      statusByElementId.set(id, 'unavailable');
      return;
    }
    const expectedBase64 = bufferToBase64(bytes);
    const match = renderedPayloads.find((p) => p.base64 === expectedBase64);
    if (match) {
      nodeByElementId.set(id, match.img);
      statusByElementId.set(id, 'available');
    } else {
      statusByElementId.set(id, 'unavailable');
    }
  }));
}
