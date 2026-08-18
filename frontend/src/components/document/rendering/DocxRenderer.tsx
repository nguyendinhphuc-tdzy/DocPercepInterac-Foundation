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
        await docxPreview.renderAsync(source, bodyRef.current, styleRef.current, {
          className: 'docx-render',
          inWrapper: true,
          breakPages: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
        });
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
