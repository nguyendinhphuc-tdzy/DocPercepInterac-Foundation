import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { EmptyState } from '../../shared/EmptyState';
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
  source, elements, selectedElementIndex, hoveredElementIndex,
  onSelectElement, onHoverElement, onEditElement, editable,
}) => {
  const bodyRef = useRef<HTMLDivElement>(null);
  const styleRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<DocxElementMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
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
        mapRef.current = buildDocxElementMap(bodyRef.current, elements);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `elements` intentionally excluded: the map is rebuilt from the same render pass, not on every element-array identity change (which happens on every edit/select and would force a full re-render otherwise).
  }, [source]);

  // Apply/clear highlight classes without touching anything else in the
  // rendered document — the overlay is a class toggle on already-rendered
  // nodes, never a re-render.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    for (const [, node] of map.nodeByIndex) {
      node.classList.remove('docx-el-selected', 'docx-el-hovered');
    }
    if (selectedElementIndex != null) {
      map.nodeByIndex.get(selectedElementIndex)?.classList.add('docx-el-selected');
    }
    if (hoveredElementIndex != null && hoveredElementIndex !== selectedElementIndex) {
      map.nodeByIndex.get(hoveredElementIndex)?.classList.add('docx-el-hovered');
    }
    if (selectedElementIndex != null) {
      map.nodeByIndex.get(selectedElementIndex)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [mapReady, selectedElementIndex, hoveredElementIndex]);

  // Delegated interaction: one listener per event type on the container,
  // resolved back to a Foundation element index via the map — rather than
  // one handler per rendered node (there can be hundreds in a real
  // document).
  useEffect(() => {
    const map = mapRef.current;
    const container = bodyRef.current;
    if (!map || !mapReady || !container) return;

    const indexForNode = (node: HTMLElement | null): number | null => {
      for (const [index, mapped] of map.nodeByIndex) {
        if (mapped === node || mapped.contains(node)) return index;
      }
      return null;
    };

    const handleOver = (e: MouseEvent) => onHoverElement(indexForNode(e.target as HTMLElement));
    const handleOut = () => onHoverElement(null);
    const handleClick = (e: MouseEvent) => {
      const index = indexForNode(e.target as HTMLElement);
      if (index == null) return;
      onSelectElement(index);
      if (editable) {
        const el = elements.find((el) => el.index === index);
        setEditingIndex(index);
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
    if (editingIndex != null) onEditElement(editingIndex, editValue);
    setEditingIndex(null);
  };

  const editingNode = editingIndex != null ? mapRef.current?.nodeByIndex.get(editingIndex) ?? null : null;
  const editingRect = editingNode?.getBoundingClientRect();
  const containerRect = bodyRef.current?.getBoundingClientRect();

  return (
    <div style={{ position: 'relative', height: '100%', overflow: 'auto' }}>
      {status === 'loading' && (
        <EmptyState icon={Loader2} iconClassName="animate-spin" title="Rendering document…" description="" />
      )}
      {status === 'error' && (
        <EmptyState icon={AlertTriangle} title="Unable to render document" description={error ?? 'This document could not be rendered.'} />
      )}
      {mapReady && !mapRef.current?.reliable && (
        <div className="renderer-notice">
          <AlertTriangle size={12} />
          <span>Element highlighting isn't available for this document — {mapRef.current?.reason}</span>
        </div>
      )}
      <div ref={styleRef} style={{ display: 'none' }} />
      <div
        ref={bodyRef}
        style={{ visibility: status === 'ready' ? 'visible' : 'hidden', padding: 'var(--space-4) 0' }}
      />
      {editingIndex != null && editingRect && containerRect && (
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
              if (e.key === 'Escape') { e.preventDefault(); setEditingIndex(null); }
            }}
          />
        </div>
      )}
    </div>
  );
};
