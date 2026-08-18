import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { EmptyState } from '../../shared/EmptyState';
import type { DocumentRendererProps } from './types';
import type { AnchorPDF } from '../../../types/element';

const RENDER_SCALE = 1.5; // fixed render scale — crisp on standard displays without full devicePixelRatio-sized canvases for every page.

interface PageState {
  pageNumber: number;
  width: number;
  height: number;
  rendered: boolean;
}

// Real PDF.js page rendering (canvas), not the extracted-text-card
// reconstruction the previous "Original" mode used. Pages render lazily —
// only when scrolled near — via IntersectionObserver, per this phase's
// explicit "do not render all PDF pages at full resolution simultaneously"
// requirement; off-screen pages keep a correctly-sized placeholder so
// scroll height stays stable.
export const PdfRenderer: React.FC<DocumentRendererProps> = ({
  source, elements, selectedElementIndex, hoveredElementIndex, onSelectElement, onHoverElement,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRefs = useRef(new Map<number, HTMLCanvasElement>());
  const pageRefs = useRef(new Map<number, HTMLDivElement>());
  const pdfDocRef = useRef<any>(null);
  const renderedPages = useRef(new Set<number>());
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [pages, setPages] = useState<PageState[]>([]);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setError(null);
    setPages([]);
    pdfDocRef.current = null;
    renderedPages.current = new Set();

    (async () => {
      try {
        const pdfjsLib = await import('pdfjs-dist');
        const workerUrl = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default;
        pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

        // pdf.js transfers (detaches) the ArrayBuffer it's given to its
        // worker via postMessage — pass a copy so the original, held in
        // useDocumentBytes' state, survives a remount (React StrictMode's
        // double-invoke in dev surfaced this: the second mount otherwise
        // hits an already-detached buffer) or a later re-render.
        const loadingTask = pdfjsLib.getDocument({ data: source.slice(0) });
        const pdf = await loadingTask.promise;
        if (cancelled) return;
        pdfDocRef.current = pdf;

        const pageStates: PageState[] = [];
        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i);
          const viewport = page.getViewport({ scale: RENDER_SCALE });
          pageStates.push({ pageNumber: i, width: viewport.width, height: viewport.height, rendered: false });
        }
        if (cancelled) return;
        setPages(pageStates);
        setStatus('ready');
      } catch (err) {
        if (!cancelled) {
          setStatus('error');
          setError(err instanceof Error ? err.message : 'Failed to render this PDF.');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [source]);

  const renderPage = async (pageNumber: number) => {
    if (renderedPages.current.has(pageNumber) || !pdfDocRef.current) return;
    const canvas = canvasRefs.current.get(pageNumber);
    if (!canvas) return;
    renderedPages.current.add(pageNumber);
    const page = await pdfDocRef.current.getPage(pageNumber);
    const viewport = page.getViewport({ scale: RENDER_SCALE });
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    await page.render({ canvasContext: ctx, viewport, canvas }).promise;
  };

  // Lazy render: observe each page placeholder, render its canvas once it
  // (or its near-neighborhood) enters the viewport.
  useEffect(() => {
    if (status !== 'ready' || pages.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const pn = Number((entry.target as HTMLElement).dataset.page);
            renderPage(pn);
          }
        }
      },
      { root: containerRef.current, rootMargin: '400px 0px' }
    );
    for (const node of pageRefs.current.values()) observer.observe(node);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, pages]);

  const elementsByPage = React.useMemo(() => {
    const byPage = new Map<number, { el: (typeof elements)[number]; anchor: AnchorPDF }[]>();
    for (const el of elements) {
      if (el.anchor.format !== 'pdf') continue;
      const list = byPage.get(el.anchor.page) ?? [];
      list.push({ el, anchor: el.anchor });
      byPage.set(el.anchor.page, list);
    }
    return byPage;
  }, [elements]);

  useEffect(() => {
    if (selectedElementIndex == null) return;
    const el = elements.find((e) => e.index === selectedElementIndex);
    if (el?.anchor.format !== 'pdf') return;
    pageRefs.current.get(el.anchor.page)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [selectedElementIndex, elements]);

  if (status === 'loading') {
    return <EmptyState icon={Loader2} iconClassName="animate-spin" title="Rendering document…" description="" />;
  }
  if (status === 'error') {
    return <EmptyState icon={AlertTriangle} title="Unable to render document" description={error ?? 'This PDF could not be rendered.'} />;
  }

  return (
    <div ref={containerRef} style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', alignItems: 'center' }}>
        {pages.map((p) => (
          <div
            key={p.pageNumber}
            ref={(node) => { if (node) pageRefs.current.set(p.pageNumber, node); }}
            data-page={p.pageNumber}
            className="pdf-render-page"
            style={{ width: p.width, height: p.height, position: 'relative' }}
          >
            <canvas
              ref={(node) => { if (node) canvasRefs.current.set(p.pageNumber, node); }}
              style={{ width: '100%', height: '100%', display: 'block' }}
            />
            {(elementsByPage.get(p.pageNumber) ?? []).map(({ el, anchor }) => {
              // bbox_relative is (x, y, w, h) — origin + dimensions, scale
              // 0-1 — per perception/models.py's own field comment. NOT two
              // corner points; treating it as (x0,y0,x1,y1) produces
              // negative/zero-sized boxes (verified against a real fixture
              // before landing this).
              const [x, y, w, h] = anchor.bbox_relative;
              const isSelected = selectedElementIndex === el.index;
              const isHovered = hoveredElementIndex === el.index;
              return (
                <div
                  key={el.index}
                  className={`pdf-el-box ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
                  style={{
                    position: 'absolute',
                    left: `${x * 100}%`,
                    top: `${y * 100}%`,
                    width: `${w * 100}%`,
                    height: `${h * 100}%`,
                  }}
                  onMouseEnter={() => onHoverElement(el.index)}
                  onMouseLeave={() => onHoverElement(null)}
                  onClick={() => onSelectElement(el.index)}
                  title={el.text}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
