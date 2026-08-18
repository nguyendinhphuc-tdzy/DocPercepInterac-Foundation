import type { ElementRowData } from '../types/element';

// The one legacy-fallback point for the canonical interaction identity —
// `element_id` is optional in the wire type purely for defensive typing
// (the backend always sends it: perception/element_classifier.py's
// `_stable_element_id`, deterministic across re-parses of an unchanged
// document). Every selection/hover/highlight/mapping surface in the
// frontend must resolve identity through this function, never by reading
// `.index` directly, so there is exactly one place that ever falls back to
// index-as-identity — not two independently-mutable identity systems (see
// the Foundation Document Perception & Renderer Contract Hardening phase).
export function idOf(el: ElementRowData): string {
  return el.element_id ?? String(el.index);
}
