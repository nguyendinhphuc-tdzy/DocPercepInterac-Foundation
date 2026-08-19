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

  mapFootnotes(container, elements, nodeByElementId, statusByElementId);
  mapTextFlowElements(container, elements, nodeByElementId, statusByElementId);
  await mapTableCells(container, elements, nodeByElementId, statusByElementId);
  await mapImages(container, elements, nodeByElementId, statusByElementId, fetchMediaBytes);
  mapDrawings(container, elements, nodeByElementId, statusByElementId);
  markUnmappableAsUnavailable(elements, statusByElementId);

  const report = buildReport(elements, statusByElementId);
  return { nodeByElementId, statusByElementId, report };
}

function markUnmappableAsUnavailable(elements: ElementRowData[], statusByElementId: Map<string, MappingStatus>) {
  // Anything not attempted above (chart/header/footer/comment/annotation)
  // has no DOM region this phase maps to — matches its own honest
  // `capabilities.selectable=false` from the backend
  // (perception/element_classifier.py). Recorded explicitly as
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

// ── Text flow (heading/para/footnote/endnote/footer/header/comment):
// PRE-LAYOUT (style_id, text[:50]) post-pass — not `.textContent` read back
// AFTER layout, and not a whole-document positional zip.
//
// The previous approach read `node.textContent` off the fully laid-out DOM
// and zipped it 1:1 against Foundation's element order. Two things broke
// that on a real 847-element KPMG fixture (526/847 = 62%): (1) layout can
// introduce numbering/field/tab content into `.textContent` that never
// existed in the source run text Foundation's `el.text` was built from, and
// (2) footnote/footer nodes sit outside whatever single "paragraph flow"
// the old zip walked, so they were never attempted at all (0/25, 0/1).
//
// This computes the SAME key from BOTH sides instead:
//   - Frontend: `onElementRendered` (DocxRenderer.tsx, via the
//     patches/docx-preview+0.4.0.patch hook) stamps `data-el-style` /
//     `data-el-rawtext` on every rendered <p> at the moment docx-preview
//     renders it — using the PRE-LAYOUT `elem` (raw <w:t> run text, the
//     same source rawTextOf() reads — see DocxRenderer.tsx for why it
//     matches python-docx's Run.text semantics field-by-field, verified
//     empirically against this exact fixture before this was written).
//   - Backend: `anchor.style_id` + `el.text` are already on the wire.
//
// One exception: `anchor.style_id` for footnote/endnote/footer/header/
// comment is NOT a real Word paragraph style — anchor_builder.py
// deliberately repurposes that field to hold a coarse type tag ("footer",
// "footnote", ...) for those kinds, since they have no body paragraph_index
// to anchor by. Keying those by (style_id, text) would compare a synthetic
// tag against a real rendered Word style and never match. So the key
// formation branches: heading/para use (real style_id, text); the five
// chrome kinds use (el.type, text) instead — still two-sided-consistent
// (the frontend side substitutes the rendered node's OWN context type,
// resolved from which docx-preview render region produced it), just not
// conflating a synthetic backend tag with an actual style name.
// footnote/endnote are deliberately NOT here — they have a reliable exact
// identity (the OOXML w:id, via mapFootnotes below) and are excluded from
// this text-matching path entirely, rather than falling through to it as a
// fallback, so a text-match can never silently overwrite a correct id-based
// match. header/footer/comment have no equivalent id and stay text-matched.
const CHROME_TYPES = new Set(['footer', 'header', 'comment']);
const NOTE_TYPES = new Set(['footnote', 'endnote']);

function textKey(styleOrType: string, text: string): string {
  return `${styleOrType} ${text.trim().slice(0, 50)}`;
}

// For text that is ALREADY in its final (trim + slice-to-50) form — read
// straight from `data-el-rawtext`, which DocxRenderer.tsx computes as
// `rawTextOf(elem).trim().slice(0, 50)` at stamp time. Must NOT be run
// through textKey()'s own `.trim()` a second time.
//
// Confirmed root cause of every one of the KPMG fixture's previously-
// unmapped para/footnote elements (17/17, verified individually): when
// the 50-char cut lands right after a word — routine in prose — the
// pre-sliced string ends in a trailing space that is a genuine, load-
// bearing part of that 50-char prefix, not incidental whitespace.
// textKey()'s `.trim()` (correct for the FULL untruncated backend text,
// where trimming BEFORE slicing only strips real leading/trailing
// whitespace) would silently strip that trailing space a second time
// here, shortening the rendered-side key to 49 characters and permanently
// desyncing it from the backend's 50-character key — every paragraph
// whose cut point happened to fall on whitespace went unavailable, not
// because of any missing render or genuine content difference.
function prebuiltKey(styleOrType: string, prebuiltText: string): string {
  return `${styleOrType} ${prebuiltText}`;
}

function mapTextFlowElements(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
) {
  const textFlowElements = elements.filter(
    (el) => el.type === 'heading' || el.type === 'para' || CHROME_TYPES.has(el.type)
  );
  if (textFlowElements.length === 0) return;

  const renderedNodes = Array.from(container.querySelectorAll<HTMLElement>('p[data-el-rawtext]'))
    .filter((node) => !node.closest('table') && (node.dataset.elRawtext ?? '').length > 0);

  // idsByKey / renderedByKey: ordered occurrence lists per exact key, built
  // independently on each side, then zipped by ordinal WITHIN each key —
  // never across the whole document. heading/para use the node's own
  // stamped style; the chrome kinds ignore style entirely (per the header
  // above) and key on text alone, disambiguated by rendering region context
  // isn't available from a flat <p> query, so they fall back to text-only
  // matching, ordinal-disambiguated the same way as everything else.
  const renderedByKey = new Map<string, HTMLElement[]>();
  for (const node of renderedNodes) {
    const style = node.dataset.elStyle || 'Normal';
    const text = node.dataset.elRawtext ?? '';
    for (const key of [prebuiltKey(style, text), prebuiltKey('__text_only__', text)]) {
      const list = renderedByKey.get(key) ?? [];
      list.push(node);
      renderedByKey.set(key, list);
    }
  }

  const seenOrdinal = new Map<string, number>();
  for (const el of textFlowElements) {
    const id = idOf(el);
    const text = el.text.trim();
    if (!text) {
      statusByElementId.set(id, 'unavailable'); // no content signal to match by at all
      continue;
    }
    const isChrome = CHROME_TYPES.has(el.type);
    const anchorStyle = isDocxAnchor(el.anchor) ? el.anchor.style_id : '';
    const key = isChrome ? textKey('__text_only__', text) : textKey(anchorStyle || 'Normal', text);

    const ordinal = seenOrdinal.get(key) ?? 0;
    seenOrdinal.set(key, ordinal + 1);

    const candidates = renderedByKey.get(key);
    const node = candidates?.[ordinal];
    if (node) {
      nodeByElementId.set(id, node);
      // "ambiguous" (not "available") when this exact key repeats more
      // often on one side than we can be fully certain corresponds 1:1 on
      // the other — still interactive (best candidate used), but the
      // caller can distinguish full confidence from a repeated-boilerplate
      // best-effort match. `balanced` per the spec: ids.length === nodes.length.
      const totalFoundationForKey = textFlowElements.filter((e) => {
        const eIsChrome = CHROME_TYPES.has(e.type);
        const eStyle = isDocxAnchor(e.anchor) ? e.anchor.style_id : '';
        const eKey = eIsChrome ? textKey('__text_only__', e.text.trim()) : textKey(eStyle || 'Normal', e.text.trim());
        return eKey === key;
      }).length;
      statusByElementId.set(id, (candidates?.length ?? 0) === totalFoundationForKey ? 'available' : 'ambiguous');
    } else {
      statusByElementId.set(id, 'unavailable');
    }
  }
}

// ── Footnotes/endnotes: exact w:id match ────────────────────────────────────
//
// Unlike header/footer/comment (no equivalent id exists in the OOXML — see
// CHROME_TYPES above), a footnote/endnote's real identity — the `w:id` from
// footnotes.xml/endnotes.xml — survives all the way to the rendered DOM:
// docx-preview parses each note into its own object carrying `.id` (that
// same w:id), renders it as one <li>, and DocxRenderer.tsx's
// onElementRendered stamps it as `data-note-id`. anchor_builder.py sets
// anchor.note_id from the identical id at parse time. A direct id match,
// same shape as mapDrawings' docPr matching — never text-content guessing,
// never positional.
function mapFootnotes(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
) {
  const noteElements = elements.filter((el) => NOTE_TYPES.has(el.type) && isDocxAnchor(el.anchor));
  if (noteElements.length === 0) return;

  const renderedByNoteId = new Map<string, HTMLElement>();
  for (const node of container.querySelectorAll<HTMLElement>('[data-note-id]')) {
    const kind = node.dataset.noteKind; // 'footnote' | 'endnote' — same w:id numbering can collide across the two parts
    const id = node.dataset.noteId;
    if (!kind || !id) continue;
    const compositeKey = `${kind}:${id}`;
    if (!renderedByNoteId.has(compositeKey)) renderedByNoteId.set(compositeKey, node);
  }

  for (const el of noteElements) {
    const id = idOf(el);
    const noteId = isDocxAnchor(el.anchor) ? el.anchor.note_id : null;
    if (!noteId) {
      statusByElementId.set(id, 'unavailable'); // no w:id was ever recorded for this note
      continue;
    }
    const node = renderedByNoteId.get(`${el.type}:${noteId}`);
    if (node) {
      nodeByElementId.set(id, node);
      statusByElementId.set(id, 'available');
    } else {
      // w:id known, but docx-preview didn't render a matching <li> for it —
      // honestly unavailable, never guessed by position or text.
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

// Full (untrimmed-per-paragraph, untruncated) text of one rendered table
// cell, reconstructed from the pre-layout `data-el-fulltext` DocxRenderer.tsx
// stamps on every <p> — mirrors python-docx's `_Cell.text` EXACTLY:
// `'\n'.join(paragraph.text for paragraph in self.paragraphs)`. Reading
// `.textContent` off the laid-out DOM instead (the previous approach) is
// what caused whole tables to go unavailable on the real KPMG fixture: a
// footnote reference renders as visible superscript text docx-preview draws
// itself (never part of the parsed `elem` tree `data-el-fulltext` is built
// from — see rawTextOf's footnoteReference case), and a `<w:br/>` becomes a
// literal '\n' in python-docx's text but produces no character at all in
// `.textContent`. Both silently changed the header-row hash on the frontend
// side only, permanently failing that table's hash match.
//
// Scoped to `p.closest('td, th') === cell`: a nested table's own paragraphs
// must never bleed into the HOST cell's text, matching python-docx's
// `_Cell.paragraphs` (direct children of this `<w:tc>` only).
function cellFullText(cell: HTMLElement): string {
  const paragraphs = Array.from(cell.querySelectorAll<HTMLElement>('p[data-el-fulltext]')).filter(
    (p) => p.closest('td, th') === cell,
  );
  return paragraphs.map((p) => p.dataset.elFulltext ?? '').join('\n');
}

async function computeHeaderHash(table: HTMLTableElement): Promise<string> {
  const firstRow = table.rows[0]; // native property: this table's own rows only, never a nested table's
  const headerText = firstRow
    ? Array.from(firstRow.cells) // native property: this row's own cells only
        .map((cell) => {
          const t = cellFullText(cell).trim();
          const span = cell.colSpan || 1;
          return t.repeat(span);
        })
        .join('')
    : '';
  return sha256Hex8(headerText);
}

// Builds a (row_index, col_index) -> rendered <td>/<th> map for ONE table,
// expanding colSpan/rowSpan exactly like the browser's own table-layout
// algorithm. Needed because python-docx's `row.cells` — what row_index/
// col_index are computed from (perception/parser.py) — repeats the SAME
// `_Cell` object at every grid position a merge spans, while the rendered
// HTML instead collapses a horizontal merge into one wider <td colSpan=N>
// and represents a vertical merge as a rowSpan on the origin <td> plus a
// hidden-but-still-present continuation <td> in every row it spans
// (docx-preview's renderTableCell: `result.style.display = "none"`, never
// omitted from the DOM). Multiple logical (row,col) coordinates legitimately
// resolving to the SAME DOM node here is correct — e.g. both (0,0) and
// (0,1) under a colSpan=2 header cell — not a bug, and never a positional
// fallback: every entry is still derived from this specific table's actual
// rendered structure, not document order.
function buildLogicalGrid(table: HTMLTableElement): Map<string, HTMLElement> {
  const grid = new Map<string, HTMLElement>();
  const carry = new Map<number, { node: HTMLElement; remaining: number }>();
  const rows = Array.from(table.rows);
  rows.forEach((row, r) => {
    const cells = Array.from(row.cells);
    let col = 0;
    let i = 0;
    while (i < cells.length || carry.has(col)) {
      const carried = carry.get(col);
      if (carried) {
        grid.set(`${r},${col}`, carried.node);
        carried.remaining -= 1;
        if (carried.remaining <= 0) carry.delete(col);
        // docx-preview still emits a real (hidden) <td> for this row/column
        // even though it's a vMerge continuation — consume it here so the
        // left-to-right walk doesn't also count it as a separate cell.
        if (i < cells.length && cells[i].style.display === 'none') i += 1;
        col += 1;
        continue;
      }
      const cell = cells[i];
      if (!cell) break;
      i += 1;
      const colSpan = cell.colSpan || 1;
      const rowSpan = cell.rowSpan || 1;
      for (let k = 0; k < colSpan; k++) grid.set(`${r},${col + k}`, cell);
      if (rowSpan > 1) {
        for (let k = 0; k < colSpan; k++) carry.set(col + k, { node: cell, remaining: rowSpan - 1 });
      }
      col += colSpan;
    }
  });
  return grid;
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

  // Only tables docx-preview rendered as part of the body flow. A header/
  // footer repeats its OWN table (e.g. a letterhead block) outside body
  // reading order — python-docx's `doc.tables` never includes those, so
  // leaving them as hash candidates risks a real body table silently
  // resolving to a structurally unrelated header/footer table that just
  // happens to share header-row text. A table nested inside another
  // table's cell is excluded for the same reason (`doc.tables` is
  // top-level/non-recursive).
  const renderedTables = Array.from(container.querySelectorAll<HTMLTableElement>('table')).filter(
    (t) => !t.closest('header, footer') && !t.closest('td, th'),
  );
  // sha256(header-row-text)[:8] is async (Web Crypto) but there are
  // typically few tables per document — computing all hashes up front,
  // then matching each Foundation table by hash rather than position, is
  // simple and keeps every table's resolution independent of the others.
  const hashed = await Promise.all(renderedTables.map(async (table) => ({ table, hash: await computeHeaderHash(table) })));
  const tablesByHash = new Map<string, HTMLTableElement[]>();
  for (const { table, hash } of hashed) {
    const list = tablesByHash.get(hash) ?? [];
    list.push(table);
    tablesByHash.set(hash, list);
  }

  const seenTableOrdinal = new Map<string, number>();
  for (const [, cells] of tableGroups) {
    const expectedHash = cells.find((c) => isDocxAnchor(c.anchor))?.anchor;
    const tableHash = expectedHash && isDocxAnchor(expectedHash) ? expectedHash.table_hash : null;
    const candidates = tableHash ? tablesByHash.get(tableHash) : undefined;

    if (!candidates || candidates.length === 0) {
      for (const cell of cells) statusByElementId.set(idOf(cell), 'unavailable');
      continue;
    }

    const ordinal = seenTableOrdinal.get(tableHash!) ?? 0;
    seenTableOrdinal.set(tableHash!, ordinal + 1);

    const targetTable = candidates[ordinal];
    if (!targetTable) {
      for (const cell of cells) statusByElementId.set(idOf(cell), 'unavailable');
      continue;
    }

    // Balanced per spec: candidates.length === totalFoundationTablesWithThisHash
    const totalFoundationTablesWithThisHash = Array.from(tableGroups.values()).filter((groupCells) => {
      const h = groupCells.find((c) => isDocxAnchor(c.anchor))?.anchor;
      return h && isDocxAnchor(h) ? h.table_hash === tableHash : false;
    }).length;

    const isBalanced = candidates.length === totalFoundationTablesWithThisHash;
    const grid = buildLogicalGrid(targetTable);
    for (const cell of cells) {
      if (!isDocxAnchor(cell.anchor)) continue;
      const r = cell.anchor.row_index ?? 0;
      const c = cell.anchor.col_index ?? 0;
      const cellNode = grid.get(`${r},${c}`);
      const id = idOf(cell);
      if (cellNode) {
        nodeByElementId.set(id, cellNode);
        statusByElementId.set(id, isBalanced ? 'available' : 'ambiguous');
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

// ── Drawings (shapes — not bitmap pictures, those are 'image' above):
// docPr @id match ──────────────────────────────────────────────────────────
//
// A shape has no byte content to hash (it's vector-described XML, not a
// stored raster) and no text signal reliable enough to key on (many are
// unlabelled). Its only stable identity is the OOXML `docPr` element's
// `id` attribute — upstream docx-preview parses `<wp:docPr>` inside
// `parseDrawingWrapper` but discards it entirely; patches/docx-preview+
// 0.4.0.patch adds a `case "docPr":` there to keep it as
// `result.foundationDrawingId`, and DocxRenderer.tsx's `onElementRendered`
// stamps it onto the rendered <div> as `data-drawing-id`. This matches it
// directly against `anchor.drawing_id` (perception/anchor_builder.py sets
// this from the same docPr id at parse time) — a real 1:1 identity match,
// not a positional or content-hash fallback.
function mapDrawings(
  container: HTMLElement,
  elements: ElementRowData[],
  nodeByElementId: Map<string, HTMLElement>,
  statusByElementId: Map<string, MappingStatus>,
) {
  const drawingElements = elements.filter((el) => el.type === 'drawing' && isDocxAnchor(el.anchor));
  if (drawingElements.length === 0) return;

  const renderedByDrawingId = new Map<string, HTMLElement>();
  for (const node of container.querySelectorAll<HTMLElement>('[data-drawing-id]')) {
    const id = node.dataset.drawingId;
    if (id && !renderedByDrawingId.has(id)) renderedByDrawingId.set(id, node);
  }

  for (const el of drawingElements) {
    const id = idOf(el);
    const drawingId = isDocxAnchor(el.anchor) ? el.anchor.drawing_id : null;
    if (!drawingId) {
      statusByElementId.set(id, 'unavailable'); // no docPr id was ever recorded for this shape
      continue;
    }
    const node = renderedByDrawingId.get(drawingId);
    if (node) {
      nodeByElementId.set(id, node);
      statusByElementId.set(id, 'available');
    } else {
      // docPr id known, but no rendered <div> carries it — either
      // docx-preview didn't render this specific shape at all (e.g. a VML
      // fallback path with no docPr, or a shape type it drops), or it's
      // nested somewhere `onElementRendered` never fires for. Honestly
      // unavailable — never guessed by position.
      statusByElementId.set(id, 'unavailable');
    }
  }
}
