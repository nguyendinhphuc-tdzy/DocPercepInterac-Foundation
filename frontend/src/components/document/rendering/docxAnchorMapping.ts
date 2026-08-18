import type { AnchorDOCX, ElementRowData } from '../../../types/element';

function isDocxAnchor(anchor: ElementRowData['anchor']): anchor is AnchorDOCX {
  return anchor.format === 'docx';
}

export interface DocxElementMap {
  // element index -> the specific rendered DOM node representing it
  // (a paragraph/heading node, or one table cell's node).
  nodeByIndex: Map<number, HTMLElement>;
  // false when the mapping could not be trusted (see buildDocxElementMap) —
  // callers must not attempt hover/select/edit interaction in that case.
  reliable: boolean;
  reason?: string;
}

// docx-preview (github.com/VolodymyrBaydalka/docxjs) exposes no built-in
// mapping from its rendered HTML back to source paragraph/table identity —
// confirmed by inspecting its docs and API surface before choosing this
// strategy (see the phase assessment). It renders one <p>/<hN>-equivalent
// element per Word paragraph, in true document order, INCLUDING empty
// paragraphs — whereas Foundation's `paragraph_index` (parser.py) only
// counts non-empty ones. So this maps by POSITION, not by paragraph_index
// value directly:
//
//   1. Collect Foundation's non-table elements (headings/paragraphs), in
//      their existing array order — which is already true document order.
//   2. Collect the container's rendered paragraph-like nodes NOT inside a
//      <table>, in DOM order, and drop any with empty text content (to
//      match Foundation's own exclusion of empty paragraphs).
//   3. If the two filtered lists are the same length, zip them 1:1 — both
//      walk the same document in the same order, and the one known
//      divergence (empty paragraphs) has just been normalized away on both
//      sides.
//   4. If the lengths disagree, something about this document's structure
//      broke that assumption (e.g. docx-preview merged/split a paragraph
//      differently than expected) — mark the mapping unreliable rather
//      than guess, per the explicit "do not silently highlight a random
//      region" requirement.
//
// Tables map differently and more reliably: python-docx's `doc.tables`
// (which parser.py/anchor_builder.py iterate to assign `table_index`) and
// docx-preview's rendered <table> elements both walk top-level tables in
// document order, so the Nth rendered <table> corresponds to table_index N
// — no text matching needed, just row_index/col_index -> <tr>/<td> lookup.
export function buildDocxElementMap(container: HTMLElement, elements: ElementRowData[]): DocxElementMap {
  const nodeByIndex = new Map<number, HTMLElement>();

  // Only text-flow elements (heading/para) participate in the paragraph
  // zip below — NOT every non-cell element. Images/charts/drawings/
  // headers/footers/footnotes/endnotes/comments are separate content
  // (images below; the rest have no DOM region this phase maps to at all,
  // matching their honest `capabilities.selectable=false` from the backend
  // — see perception/element_classifier.py).
  const textFlowElements = elements.filter((el) => el.type === 'heading' || el.type === 'para');

  const allParaLike = Array.from(
    container.querySelectorAll<HTMLElement>('p, h1, h2, h3, h4, h5, h6')
  ).filter((node) => !node.closest('table') && node.querySelector('img') == null);
  const nonEmptyParaLike = allParaLike.filter((node) => (node.textContent ?? '').trim().length > 0);

  if (nonEmptyParaLike.length !== textFlowElements.length) {
    return {
      nodeByIndex,
      reliable: false,
      reason: `Rendered paragraph count (${nonEmptyParaLike.length}) does not match Foundation's heading/paragraph count (${textFlowElements.length}) — mapping would be guesswork.`,
    };
  }

  textFlowElements.forEach((el, i) => {
    nodeByIndex.set(el.index, nonEmptyParaLike[i]);
  });

  // Images: Foundation's IMAGE elements are already in true document order
  // (parser.py interleaves them at their actual paragraph position — see
  // its module docstring), and docx-preview renders one <img> per picture
  // in that same order, so a positional zip is reliable under the same
  // "counts must match" guard as everything else here. Rendered as <img>
  // specifically because DocxRenderer.tsx passes `useBase64URL: true`.
  const imageElements = elements.filter((el) => el.type === 'image' && isDocxAnchor(el.anchor));
  const renderedImages = Array.from(container.querySelectorAll<HTMLImageElement>('img')).filter((img) => !img.closest('table'));
  let imagesReliable = true;
  let imagesReason: string | undefined;
  if (imageElements.length > 0) {
    if (renderedImages.length !== imageElements.length) {
      imagesReliable = false;
      imagesReason = `Rendered image count (${renderedImages.length}) does not match Foundation's image element count (${imageElements.length}) — images in this document will not be interactive.`;
    } else {
      imageElements.forEach((el, i) => {
        nodeByIndex.set(el.index, renderedImages[i]);
      });
    }
  }

  // Tables: group Foundation cell elements by table_index (preserving row/col),
  // then zip against the Nth rendered <table> in document order.
  const tableGroups = new Map<number, ElementRowData[]>();
  for (const el of elements) {
    if (el.type === 'cell' && isDocxAnchor(el.anchor) && el.anchor.table_index !== null && el.anchor.table_index !== undefined) {
      const list = tableGroups.get(el.anchor.table_index) ?? [];
      list.push(el);
      tableGroups.set(el.anchor.table_index, list);
    }
  }
  const orderedTableIndices = Array.from(tableGroups.keys()).sort((a, b) => a - b);
  const renderedTables = Array.from(container.querySelectorAll<HTMLTableElement>('table'));

  if (renderedTables.length !== orderedTableIndices.length) {
    // Paragraph mapping can still be trusted even if table mapping can't —
    // but tables in this document won't be interactive. Not fatal overall.
    const tableReason = orderedTableIndices.length > 0
      ? `Rendered table count (${renderedTables.length}) does not match Foundation table count (${orderedTableIndices.length}) — tables in this document will not be interactive.`
      : undefined;
    return { nodeByIndex, reliable: imagesReliable, reason: imagesReason ?? tableReason };
  }

  orderedTableIndices.forEach((tableIndex, tablePos) => {
    const tableNode = renderedTables[tablePos];
    const rows = Array.from(tableNode.querySelectorAll<HTMLTableRowElement>('tr'));
    for (const el of tableGroups.get(tableIndex) ?? []) {
      if (!isDocxAnchor(el.anchor)) continue;
      const r = el.anchor.row_index ?? 0;
      const c = el.anchor.col_index ?? 0;
      const row = rows[r];
      if (!row) continue;
      const cell = row.querySelectorAll<HTMLElement>('td, th')[c];
      if (cell) nodeByIndex.set(el.index, cell);
    }
  });

  return { nodeByIndex, reliable: imagesReliable, reason: imagesReason };
}
