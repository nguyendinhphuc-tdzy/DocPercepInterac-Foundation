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


def _load_workflow_context(session_id: str, user_id: str = "anonymous") -> Optional[dict[str, Any]]:
    """Structured workflow context for this session, or None.

    Read from the canonical workflow repository — never from the browser, never
    from a filename, and never from container-local disk (Render discards that
    on restart, which would silently strip the Agent's workflow context after a
    redeploy). No intake for this session simply means "generic workspace".
    """
    try:
        from adapters.repository import get_repositories
        from applications.rollforward.workflow_intake import WorkflowIntakeSession

        repos = get_repositories()
        workflow = repos.workflows.get_workflow(session_id, user_id=user_id)
        if workflow is None:
            return None
        assignments = repos.workflows.list_assignments(workflow.workflow_id, user_id=user_id)
        return WorkflowIntakeSession.from_records(workflow, assignments).agent_workflow_context()
    except Exception:
        return None


def _available_documents(session_id: str, session_dir: Path,
                         user_id: str = "anonymous") -> list[dict[str, Any]]:
    """The session's documents, from the canonical repository.

    `manifest.json` is a local development/test mirror of the same data, not the
    production authority: it lives on the container's ephemeral disk. It is still
    consulted as a fallback so a locally-seeded session (and the existing test
    suite, which seeds exactly that way) keeps working.
    """
    try:
        from adapters.repository import get_repositories

        records = get_repositories().documents.list_documents(session_id, user_id=user_id)
    except Exception:
        records = []

    if records:
        return [{
            "doc_id": doc.doc_id,
            "filename": doc.original_filename,
            "format": doc.format,
            "status": doc.status,
            "element_count": doc.element_count,
        } for doc in records]

    manifest = _load_manifest(session_dir)
    return [{
        "doc_id": doc_id,
        "filename": entry.get("original_filename", ""),
        "format": entry.get("format", ""),
        "status": entry.get("status", "unknown"),
        "element_count": entry.get("element_count", 0),
    } for doc_id, entry in manifest.get("documents", {}).items()]


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
        interaction: Optional[Any] = None,
    ) -> AgentContext:
        """Assemble the request's context, evidence first.

        Priority, highest first:

            1. verified selected evidence — what the user actually pointed at
            2. the active document
            3. the generic workspace listing

        `interaction` is a VerifiedInteractionContext: already checked for
        ownership and existence, with its metadata rebuilt from the documents.
        """
        context = AgentContext(
            session_id=session_id,
            active_doc_id=active_doc_id,
            selected_element=None,
            available_documents=[],
            relevant_elements=[],
        )

        if interaction is not None:
            context.interaction_context = interaction.to_dict()
            context.selected_evidence = [s.to_dict() for s in interaction.selected_elements]
            if interaction.selected_elements:
                # The selection carries its OWN document id, so it resolves even
                # when the workspace holds many documents and none is "active" —
                # the case where selection used to be silently dropped.
                first = interaction.selected_elements[0]
                context.selected_element = {
                    "doc_id": first.document_id,
                    "doc_name": first.document_name,
                    "element_id": first.element_id,
                    "name": first.display_label,
                    "type": first.element_type,
                    "text": first.text,
                    "capabilities": first.capabilities,
                    "anchor": first.anchor,
                }
                context.active_doc_id = active_doc_id or first.document_id
            if interaction.active_document_id and not context.active_doc_id:
                context.active_doc_id = interaction.active_document_id

        if not session_id:
            return context

        session_dir = UPLOAD_ROOT / session_id

        # Both of these read canonical state first (repository), then fall back
        # to the local mirror — so a session survives a container restart, and a
        # locally-seeded session still resolves.
        context.workflow = _load_workflow_context(session_id)
        context.available_documents = _available_documents(session_id, session_dir)

        if not context.available_documents and not session_dir.is_dir():
            return context

        # If active doc is not explicitly specified, default to first document ONLY if exactly 1 document is loaded
        effective_doc_id = context.active_doc_id or active_doc_id
        if not effective_doc_id:
            if len(context.available_documents) == 1:
                effective_doc_id = context.available_documents[0]["doc_id"]
                context.active_doc_id = effective_doc_id
            else:
                # Ambiguous document context when multiple documents are present without selection
                context.active_doc_id = None

        # Resolve selected element if requested. Skipped when verified evidence
        # already supplied it — that path is authoritative.
        if context.selected_element is None and effective_doc_id and selected_element_id:
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
