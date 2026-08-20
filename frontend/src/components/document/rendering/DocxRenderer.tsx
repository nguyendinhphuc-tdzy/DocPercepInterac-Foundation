import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { EmptyState } from '../../shared/EmptyState';
import { downloadUrlFor } from '../../../api/client';
import { buildDocxElementMap, type DocxElementMap } from './docxAnchorMapping';
import type { DocumentRendererProps } from './types';

// Allowed link schemes after rendering untrusted DOCX content to HTML —
// docx-preview builds DOM nodes directly (not innerHTML string injection),
// but a document can still legitimately contain an <a href="javascript:...">
// hyperlink relationship. Strip anything that isn't a normal web/mail link
// rather than trust the source file. Images are rendered as base64 data
// URIs (`useBase64URL: true` below) sourced only from the docx's own
// embedded media — never fetched from an external relationship — so no
// separate image sanitization is needed here.
const ALLOWED_LINK_SCHEMES = ['http:', 'https:', 'mailto:'];

// Pre-layout raw text of a docx-preview element (its parsed `elem`, before
// any DOM/CSS is applied) — mirrors python-docx's `Run.text`/`Paragraph.text`
// semantics EXACTLY, verified empirically against a real fixture (a KPMG
// Local File template, 314 top-level paragraphs) before this was written,
// not assumed from reading either library's source alone:
//   - <w:t>            -> its text
//   - <w:tab/>         -> '\t'          (python-docx: same)
//   - <w:noBreakHyphen/> -> '-'         (python-docx: same, confirmed via a
//     real STYLEREF/SEQ field construct in the fixture, even though
//     python-docx's own docstring doesn't mention it)
//   - <w:br> (line break only) -> '\n'  (python-docx: same; page/column
//     breaks are NOT text and are excluded, matching python-docx)
//   - deletedText / instruction (field codes) -> '' (python-docx: `.text`
//     is built from direct-child `<w:r>` only — CT_P.r_lst is
//     `ZeroOrMore("w:r")`, and lxml's plain-tag `findall` matches direct
//     children only, so text wrapped in `<w:ins>`/`<w:del>` a level deeper
//     is invisible to python-docx regardless; instruction text was never
//     visible content to begin with)
//   - drawing / vmlPicture -> '' and NEVER recursed into — python-docx's
//     Run.text docstring explicitly ignores `<w:drawing>`, and empirically
//     docx-preview falls back to VML (`vmlPicture`, not `drawing`) for at
//     least "wps" text-box shapes; recursing into either would pull a text
//     box's own nested paragraphs into the host paragraph's text, which is
//     exactly the discrepancy this function exists to avoid.
function rawTextOf(node: any): string {
  if (!node) return '';
  if (node.type === 'text') return node.text ?? '';
  if (node.type === 'tab') return '\t';
  if (node.type === 'noBreakHyphen') return '-';
  if (node.type === 'break') return node.break === 'textWrapping' ? '\n' : '';
  if (node.type === 'deletedText' || node.type === 'instruction') return '';
  if (node.type === 'drawing' || node.type === 'vmlPicture') return '';
  if (Array.isArray(node.children)) return node.children.map(rawTextOf).join('');
  return '';
}

function sanitizeRenderedLinks(container: HTMLElement) {
  for (const a of Array.from(container.querySelectorAll('a[href]'))) {
    const href = a.getAttribute('href') ?? '';
    try {
      const scheme = new URL(href, window.location.href).protocol;
      if (!ALLOWED_LINK_SCHEMES.includes(scheme)) {
        a.removeAttribute('href');
      } else {
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener noreferrer');
      }
    } catch {
      a.removeAttribute('href');
    }
  }
}

export const DocxRenderer: React.FC<DocumentRendererProps> = ({
  source, elements, selectedElementId, hoveredElementId,
  onSelectElement, onHoverElement, onEditElement, editable,
  sessionId, docId, onMappingReport,
}) => {
  const bodyRef = useRef<HTMLDivElement>(null);
  const styleRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<DocxElementMap | null>(null);
  // Reverse index (rendered node -> element_id), built once alongside the
  // forward map — an O(1) lookup for every mouseover/click instead of
  // scanning the whole nodeByElementId map on every event (this phase's
  // explicit performance requirement).
  const nodeToElementId = useRef(new Map<HTMLElement, string>());
  const [mapReady, setMapReady] = useState(false);
  const [editingElementId, setEditingElementId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  // Render once per `source` — docx-preview builds real DOM nodes directly
  // into bodyRef, so re-running it appends unless the container is cleared
  // first. Re-running only when the byte source changes (not on every
  // hover/select) keeps this a "render once, overlay interactions
  // incrementally" flow rather than re-converting the whole document.
  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setError(null);
    setMapReady(false);
    mapRef.current = null;
    nodeToElementId.current = new Map();

    (async () => {
      try {
        const docxPreview = await import('docx-preview');
        if (cancelled || !bodyRef.current || !styleRef.current) return;
        bodyRef.current.innerHTML = '';
        styleRef.current.innerHTML = '';
        // `onElementRendered` is our own addition (patches/docx-preview+0.4.0.patch
        // — see patch-package), not part of docx-preview's upstream Options
        // type, hence the cast. Only stamps <p> nodes: `data-el-style` /
        // `data-el-rawtext` become the (styleId, text[:50]) matching key
        // docxAnchorMapping.ts's post-pass resolves against the backend's
        // own anchor.style_id + el.text — computed from the SAME pre-layout
        // `elem` docx-preview is about to render, never from `.textContent`
        // after layout (which is what produced the 526/847 regression this
        // replaces). No `closest()` here — the node isn't attached to the
        // document tree yet at this point in rendering.
        await docxPreview.renderAsync(source, bodyRef.current, styleRef.current, {
          className: 'docx-render',
          inWrapper: true,
          breakPages: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
          onElementRendered: (elem: any, node: HTMLElement) => {
            // Shapes (type='drawing' — a shape/text-box/SmartArt, NOT a
            // bitmap picture; those are type='image', matched separately
            // by byte content in mapImages) render to a <div> (docx-preview's
            // renderDrawing: `this.toHTML(elem, ns.html, "div")`). Their
            // ONLY stable identity is docPr @id — patched into
            // parseDrawingWrapper's result as `foundationDrawingId`
            // (patches/docx-preview+0.4.0.patch), since upstream silently
            // discarded it. Stamped here, matched in docxAnchorMapping.ts's
            // mapDrawings against anchor.drawing_id.
            if (elem.foundationDrawingId != null) {
              node.setAttribute('data-drawing-id', String(elem.foundationDrawingId));
              return;
            }
            // Footnotes/endnotes render as one <li> per note (docx-preview's
            // renderNotes -> renderContainer(elem, "li")), and `elem` here is
            // docx-preview's OWN parsed WmlFootnote/WmlEndnote object, which
            // already carries the real OOXML w:id as `.id` (FootnotesPart's
            // parseNotes: `node.id = xml.attr(el, "id")`) — no docx-preview
            // patch needed, unlike drawings. Matched in docxAnchorMapping.ts's
            // mapFootnotes against anchor.note_id: an exact id match instead
            // of the text-content guessing every other chrome kind is stuck
            // with (no equivalent id exists for header/footer/comment).
            if ((elem.type === 'footnote' || elem.type === 'endnote') && node.tagName === 'LI' && elem.id != null) {
              node.setAttribute('data-note-id', String(elem.id));
              node.setAttribute('data-note-kind', elem.type);
              return;
            }
            if (node.tagName !== 'P') return;
            node.setAttribute('data-el-style', elem.styleName ?? 'Normal');
            const raw = rawTextOf(elem);
            node.setAttribute('data-el-rawtext', raw.trim().slice(0, 50));
            // Untruncated, untrimmed sibling of the above — table-cell text
            // (docxAnchorMapping.ts's table_hash recomputation) needs the
            // EXACT text python-docx's `cell.text` would produce to hash
            // identically, not a 50-char matching-key prefix. Stamped on
            // every <p> unconditionally (not just table ones): `elem` here
            // isn't attached to the document tree yet, so there's no cheap
            // way to test "is this inside a table cell" at this point.
            node.setAttribute('data-el-fulltext', raw);
          },
        } as Parameters<typeof docxPreview.renderAsync>[3]);
        if (cancelled || !bodyRef.current) return;
        sanitizeRenderedLinks(bodyRef.current);

        const fetchMediaBytes = async (mediaId: string): Promise<ArrayBuffer | null> => {
          if (!sessionId || !docId) return null;
          try {
            const res = await fetch(downloadUrlFor(`/api/documents/${sessionId}/media/${docId}/${mediaId}`));
            if (!res.ok) return null;
            return await res.arrayBuffer();
          } catch {
            return null;
          }
        };

        const map = await buildDocxElementMap(bodyRef.current, elements, fetchMediaBytes);
        if (cancelled) return;
        mapRef.current = map;
        for (const [elementId, node] of map.nodeByElementId) nodeToElementId.current.set(node, elementId);
        onMappingReport?.(map.report);
        if (typeof window !== 'undefined') (window as any).__DOCX_MAPPING_REPORT__ = map.report;
        setMapReady(true);
        setStatus('ready');
      } catch (err) {
        if (!cancelled) {
          setStatus('error');
          setError(err instanceof Error ? err.message : 'Failed to render this document.');
        }
      }
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `elements`/`onMappingReport` intentionally excluded: the map is rebuilt from the same render pass, not on every element-array identity change (which happens on every edit/select and would force a full re-render otherwise).
  }, [source, sessionId, docId]);

  // Apply/clear highlight classes without touching anything else in the
  // rendered document — the overlay is a class toggle on already-rendered
  // nodes, never a re-render. Only iterates elements that actually have a
  // resolved RenderRegion (nodeByElementId) — an unmapped element simply
  // has nothing to highlight, which is exactly the failure-isolation
  // behavior this phase requires (it never blocks highlighting others).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    for (const node of map.nodeByElementId.values()) {
      node.classList.remove('docx-el-selected', 'docx-el-hovered');
    }
    if (selectedElementId != null) {
      map.nodeByElementId.get(selectedElementId)?.classList.add('docx-el-selected');
    }
    if (hoveredElementId != null && hoveredElementId !== selectedElementId) {
      map.nodeByElementId.get(hoveredElementId)?.classList.add('docx-el-hovered');
    }
    if (selectedElementId != null) {
      map.nodeByElementId.get(selectedElementId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [mapReady, selectedElementId, hoveredElementId]);

  // Delegated interaction: one listener per event type on the container,
  // resolved back to a Foundation `element_id` via the reverse index —
  // O(1) per event, never a scan, and never DOM/array position.
  useEffect(() => {
    const container = bodyRef.current;
    if (!mapReady || !container) return;

    const elementIdForNode = (node: HTMLElement | null): string | null => {
      let current: HTMLElement | null = node;
      while (current && current !== container) {
        const id = nodeToElementId.current.get(current);
        if (id) return id;
        current = current.parentElement;
      }
      return null;
    };

    const handleOver = (e: MouseEvent) => onHoverElement(elementIdForNode(e.target as HTMLElement));
    const handleOut = () => onHoverElement(null);
    const handleClick = (e: MouseEvent) => {
      const elementId = elementIdForNode(e.target as HTMLElement);
      if (elementId == null) return;
      onSelectElement(elementId);
      const el = elements.find((el) => (el.element_id ?? String(el.index)) === elementId);
      // Per-element capability, not just the document-level `editable`
      // flag — an image/chart/drawing is selectable but never editable
      // (see perception/element_classifier.py's capabilities), so clicking
      // one must select it without popping open a text-edit box.
      if (editable && (el?.capabilities?.editable ?? true)) {
        setEditingElementId(elementId);
        setEditValue(el?.text ?? '');
      }
    };

    container.addEventListener('mouseover', handleOver);
    container.addEventListener('mouseout', handleOut);
    container.addEventListener('click', handleClick);
    return () => {
      container.removeEventListener('mouseover', handleOver);
      container.removeEventListener('mouseout', handleOut);
      container.removeEventListener('click', handleClick);
    };
  }, [mapReady, editable, elements, onHoverElement, onSelectElement]);

  const commitEdit = () => {
    if (editingElementId != null) onEditElement(editingElementId, editValue);
    setEditingElementId(null);
  };

  const editingNode = editingElementId != null ? mapRef.current?.nodeByElementId.get(editingElementId) ?? null : null;
  const editingRect = editingNode?.getBoundingClientRect();
  const containerRect = bodyRef.current?.getBoundingClientRect();

  const report = mapRef.current?.report;
  const unmappedCount = report ? report.byStatus.unavailable + report.byStatus.ambiguous : 0;

  return (
    <div style={{ position: 'relative', height: '100%', overflow: 'auto' }}>
      {status === 'loading' && (
        <EmptyState icon={Loader2} iconClassName="animate-spin" title="Rendering document…" description="" />
      )}
      {status === 'error' && (
        <EmptyState icon={AlertTriangle} title="Unable to render document" description={error ?? 'This document could not be rendered.'} />
      )}
      {mapReady && report && unmappedCount > Math.max(2, report.total * 0.05) && (
        <div className="renderer-notice">
          <AlertTriangle size={12} />
          <span>
            {unmappedCount} of {report.total} elements can't be linked to the rendered document — everything else remains interactive.
          </span>
        </div>
      )}
      <div ref={styleRef} style={{ display: 'none' }} />
      <div
        ref={bodyRef}
        style={{ visibility: status === 'ready' ? 'visible' : 'hidden', padding: 'var(--space-4) 0' }}
      />
      {editingElementId != null && editingRect && containerRect && (
        <div
          style={{
            position: 'absolute',
            left: editingRect.left - containerRect.left + (bodyRef.current?.scrollLeft ?? 0),
            top: editingRect.top - containerRect.top + (bodyRef.current?.scrollTop ?? 0),
            width: Math.max(editingRect.width, 160),
            zIndex: 5,
          }}
        >
          <textarea
            autoFocus
            className="docx-inline-edit"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitEdit(); }
              if (e.key === 'Escape') { e.preventDefault(); setEditingElementId(null); }
            }}
          />
        </div>
      )}
    </div>
  );
};
