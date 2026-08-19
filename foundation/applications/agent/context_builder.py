"""Context Builder for Foundation Agent Architecture.

Strictly consumes Foundation document storage, manifest, and perceived elements.
Does NOT create an independent parser or invent element identities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from perception.models import Element
from perception.parser import extract_geometry
from perception.anchor_builder import assign_anchors
from perception.element_classifier import classify_blocks

from applications.agent.models import AgentContext

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


def _load_manifest(session_dir: Path) -> dict:
    manifest_path = session_dir / "manifest.json"
    if not manifest_path.exists():
        return {"documents": {}}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"documents": {}}


def _current_path_for(session_dir: Path, entry: dict) -> Path:
    stored_path = session_dir / entry["stored_filename"]
    patched = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
    return patched if patched.exists() else stored_path


def perceive_session_document(session_id: str, doc_id: str) -> tuple[dict[str, Any], list[Element]]:
    """Perceives or loads elements for a document strictly through Foundation primitives."""
    session_dir = UPLOAD_ROOT / session_id
    manifest = _load_manifest(session_dir)
    entry = manifest.get("documents", {}).get(doc_id)
    if not entry:
        raise ValueError(f"Document '{doc_id}' not found in session '{session_id}'")

    file_path = _current_path_for(session_dir, entry)
    fmt = entry["format"]
    
    blocks = extract_geometry(str(file_path))
    anchors = assign_anchors(blocks, fmt)
    elements = classify_blocks(blocks, fmt, anchors)
    return entry, elements


class ContextBuilder:
    """Builds authoritative Agent context from Foundation session state."""

    @staticmethod
    def build_context(
        session_id: Optional[str],
        active_doc_id: Optional[str] = None,
        selected_element_id: Optional[str] = None,
    ) -> AgentContext:
        context = AgentContext(
            session_id=session_id,
            active_doc_id=active_doc_id,
            selected_element=None,
            available_documents=[],
            relevant_elements=[],
        )

        if not session_id:
            return context

        session_dir = UPLOAD_ROOT / session_id
        if not session_dir.is_dir():
            return context

        manifest = _load_manifest(session_dir)
        docs_dict = manifest.get("documents", {})

        for doc_id, entry in docs_dict.items():
            context.available_documents.append({
                "doc_id": doc_id,
                "filename": entry.get("original_filename", ""),
                "format": entry.get("format", ""),
                "status": entry.get("status", "unknown"),
                "element_count": entry.get("element_count", 0),
            })

        # If active doc is not explicitly specified, default to first ready document
        effective_doc_id = active_doc_id
        if not effective_doc_id and context.available_documents:
            effective_doc_id = context.available_documents[0]["doc_id"]
            context.active_doc_id = effective_doc_id

        # Resolve selected element if requested
        if effective_doc_id and selected_element_id:
            try:
                entry, elements = perceive_session_document(session_id, effective_doc_id)
                for el in elements:
                    if el.element_id == selected_element_id:
                        context.selected_element = {
                            "doc_id": effective_doc_id,
                            "doc_name": entry.get("original_filename", ""),
                            "element_id": el.element_id,
                            "name": el.name,
                            "type": el.type.value if hasattr(el.type, "value") else str(el.type),
                            "text": el.text,
                            "capabilities": el.capabilities.model_dump(mode="json"),
                            "anchor": el.anchor.model_dump(mode="json"),
                        }
                        break
            except Exception:
                pass

        return context

    @staticmethod
    def search_elements(
        session_id: str,
        doc_id: str,
        query: str,
        element_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Performs deterministic search across Foundation elements."""
        entry, elements = perceive_session_document(session_id, doc_id)
        results = []
        q_lower = query.lower().strip()

        for el in elements:
            el_type_str = el.type.value if hasattr(el.type, "value") else str(el.type)
            if element_type and el_type_str.lower() != element_type.lower():
                continue

            text_match = q_lower in el.text.lower() if el.text else False
            name_match = q_lower in el.name.lower() if el.name else False

            if text_match or name_match:
                results.append({
                    "doc_id": doc_id,
                    "doc_name": entry.get("original_filename", ""),
                    "element_id": el.element_id,
                    "name": el.name,
                    "type": el_type_str,
                    "text": el.text,
                    "capabilities": el.capabilities.model_dump(mode="json"),
                })
                if len(results) >= limit:
                    break

        return results
