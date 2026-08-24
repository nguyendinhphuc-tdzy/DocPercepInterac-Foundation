"""
Interaction context — what the user actually selected (Phase P0-A)
=================================================================
Location: foundation/applications/agent/interaction_context.py

Selecting evidence is a stateful user action, not a decorative chip. This module
is the server's half of that contract: it parses the selection the client sends,
verifies every reference against Foundation's own state, and rebuilds the
canonical metadata from the document itself.

Why verification, not trust
---------------------------
The client can name an element; it cannot be the authority on what that element
IS. Labels, coordinates and types supplied by the browser are discarded and
re-derived from the perceived document, so a stale, spoofed or simply wrong
selection cannot steer an operation.

Failure is explicit
-------------------
An invalid selection raises `InteractionContextError` and the route answers 4xx.
A selection is never silently dropped — silently ignoring it is the bug this
phase exists to fix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InteractionContextError(ValueError):
    """Raised when a selection cannot be verified against Foundation state."""

    def __init__(self, message: str, *, code: str = "invalid_selection",
                 element_id: Optional[str] = None, document_id: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.element_id = element_id
        self.document_id = document_id

    def to_payload(self) -> Dict[str, Any]:
        return {
            "error": str(self),
            "status": "error",
            "error_type": self.code,
            "element_id": self.element_id,
            "document_id": self.document_id,
        }


# ============================================================================
# WIRE FORMAT — what the client may say
# ============================================================================

class SelectedElementInput(BaseModel):
    """One selection as the client describes it. Only the ids are trusted."""
    document_id: str
    element_id: str
    element_type: Optional[str] = None      # re-derived server-side
    display_label: Optional[str] = None     # re-derived server-side
    location: Dict[str, Any] = Field(default_factory=dict)   # re-derived server-side
    selection_source: str = "document_view"


class InteractionContextInput(BaseModel):
    """The selection payload of an Agent request."""
    session_id: Optional[str] = None
    workflow_id: Optional[str] = None
    active_document_id: Optional[str] = None
    selected_elements: List[SelectedElementInput] = Field(default_factory=list)
    selected_regions: List[Dict[str, Any]] = Field(default_factory=list)
    selected_documents: List[str] = Field(default_factory=list)
    workflow_type: Optional[str] = None


# ============================================================================
# VERIFIED FORM — what the rest of the system may use
# ============================================================================

@dataclass
class VerifiedSelection:
    """One selection, rebuilt from the document it claims to come from."""
    document_id: str
    document_name: str
    element_id: str
    element_type: str
    display_label: str
    location: Dict[str, Any]
    selection_source: str
    text: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    anchor: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "display_label": self.display_label,
            "location": dict(self.location),
            "selection_source": self.selection_source,
            "text": self.text,
            "capabilities": dict(self.capabilities),
            "anchor": dict(self.anchor),
        }


@dataclass
class VerifiedInteractionContext:
    """The authoritative interaction state for one request."""
    session_id: Optional[str]
    workflow_id: Optional[str] = None
    workflow_type: Optional[str] = None
    active_document_id: Optional[str] = None
    selected_elements: List[VerifiedSelection] = field(default_factory=list)
    selected_documents: List[str] = field(default_factory=list)
    selected_regions: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_selection(self) -> bool:
        return bool(self.selected_elements)

    def telemetry(self) -> Dict[str, Any]:
        """Counts and ids only — never a cell value or a document's text."""
        return {
            "selected_element_count": len(self.selected_elements),
            "selected_document_count": len(
                {s.document_id for s in self.selected_elements} | set(self.selected_documents)),
            "selected_element_types": sorted({s.element_type for s in self.selected_elements}),
            "workflow_type": self.workflow_type,
            "has_active_document": bool(self.active_document_id),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "active_document_id": self.active_document_id,
            "selected_elements": [s.to_dict() for s in self.selected_elements],
            "selected_documents": list(self.selected_documents),
            "selected_regions": list(self.selected_regions),
        }


# ============================================================================
# VERIFICATION
# ============================================================================

class InteractionContextVerifier:
    """Turns a claimed selection into a verified one, or refuses it."""

    @classmethod
    def verify(cls, payload: Optional[Dict[str, Any]], *, session_id: Optional[str],
               user_id: str = "anonymous") -> VerifiedInteractionContext:
        """Validate ownership and existence, then rebuild canonical metadata."""
        parsed = InteractionContextInput(**(payload or {}))

        if parsed.session_id and session_id and parsed.session_id != session_id:
            raise InteractionContextError(
                "The interaction context names a different session than the request.",
                code="session_mismatch")

        verified = VerifiedInteractionContext(
            session_id=session_id or parsed.session_id,
            active_document_id=parsed.active_document_id,
            selected_regions=list(parsed.selected_regions),
        )

        cls._verify_workflow(parsed, verified, session_id, user_id)

        documents = cls._session_documents(session_id, user_id)
        for document_id in parsed.selected_documents:
            if document_id not in documents:
                raise InteractionContextError(
                    f"Document '{document_id}' is not part of this session.",
                    code="unknown_document", document_id=document_id)
            verified.selected_documents.append(document_id)

        if parsed.active_document_id and parsed.active_document_id not in documents:
            raise InteractionContextError(
                f"The active document '{parsed.active_document_id}' is not part of this session.",
                code="unknown_document", document_id=parsed.active_document_id)

        for selection in parsed.selected_elements:
            verified.selected_elements.append(
                cls._verify_element(selection, documents, session_id, user_id))

        return verified

    # ------------------------------------------------------------------

    @staticmethod
    def _verify_workflow(parsed: InteractionContextInput,
                         verified: VerifiedInteractionContext,
                         session_id: Optional[str], user_id: str) -> None:
        """The workflow is the server's to state, not the client's to assert."""
        if not session_id:
            return
        try:
            from adapters.repository import get_repositories

            workflow = get_repositories().workflows.get_workflow(session_id, user_id=user_id)
        except Exception:
            workflow = None

        if workflow is None:
            if parsed.workflow_id:
                raise InteractionContextError(
                    "This session has no workflow, so a workflow_id cannot belong to it.",
                    code="unknown_workflow")
            return

        if parsed.workflow_id and parsed.workflow_id != workflow.workflow_id:
            raise InteractionContextError(
                "The workflow_id does not belong to this session.", code="unknown_workflow")

        verified.workflow_id = workflow.workflow_id
        verified.workflow_type = workflow.workflow_type

    @staticmethod
    def _session_documents(session_id: Optional[str], user_id: str) -> Dict[str, str]:
        """{doc_id: filename} for this session — the ownership boundary."""
        if not session_id:
            return {}

        documents: Dict[str, str] = {}
        try:
            from adapters.repository import get_repositories

            for record in get_repositories().documents.list_documents(
                    session_id, user_id=user_id):
                documents[record.doc_id] = record.original_filename
        except Exception:
            pass

        if not documents:
            # Local/test sessions are seeded through the manifest the document
            # layer writes; it is the same data, one layer down.
            from applications.agent.context_builder import UPLOAD_ROOT, _load_manifest

            manifest = _load_manifest(UPLOAD_ROOT / session_id)
            for doc_id, entry in manifest.get("documents", {}).items():
                documents[doc_id] = entry.get("original_filename", "")
        return documents

    @classmethod
    def _verify_element(cls, selection: SelectedElementInput, documents: Dict[str, str],
                        session_id: Optional[str], user_id: str) -> VerifiedSelection:
        if selection.document_id not in documents:
            raise InteractionContextError(
                f"Selected element '{selection.element_id}' names document "
                f"'{selection.document_id}', which is not part of this session.",
                code="unknown_document",
                element_id=selection.element_id, document_id=selection.document_id)

        element = cls._find_element(session_id, selection.document_id, selection.element_id)
        if element is None:
            raise InteractionContextError(
                f"Selected element '{selection.element_id}' does not exist in document "
                f"'{selection.document_id}'.",
                code="unknown_element",
                element_id=selection.element_id, document_id=selection.document_id)

        anchor = element.anchor.model_dump(mode="json")
        element_type = (element.type.value if hasattr(element.type, "value")
                        else str(element.type))
        return VerifiedSelection(
            document_id=selection.document_id,
            document_name=documents[selection.document_id],
            element_id=element.element_id,
            # Type, label and location are re-derived: whatever the client sent
            # for them is discarded.
            element_type=element_type,
            display_label=element.name or element_type,
            location=cls._location_from_anchor(anchor),
            selection_source=selection.selection_source,
            text=element.text or "",
            capabilities=element.capabilities.model_dump(mode="json"),
            anchor=anchor,
        )

    @staticmethod
    def _find_element(session_id: Optional[str], document_id: str, element_id: str):
        if not session_id:
            return None
        from applications.agent.context_builder import perceive_session_document

        try:
            _entry, elements = perceive_session_document(session_id, document_id)
        except Exception:
            return None
        for element in elements:
            if element.element_id == element_id:
                return element
        return None

    @staticmethod
    def _location_from_anchor(anchor: Dict[str, Any]) -> Dict[str, Any]:
        """Whatever Foundation already knows about where this element lives.

        Nothing is invented: the keys are copied straight out of the canonical
        anchor for the format the element belongs to.
        """
        keys = (
            "format", "sheet_name", "cell_address", "from_cell", "to_cell",
            "paragraph_index", "table_index", "row_index", "col_index",
            "page_number", "drawing_id", "media_id", "run_index",
        )
        return {key: anchor[key] for key in keys if key in anchor and anchor[key] is not None}


__all__ = [
    "InteractionContextError",
    "SelectedElementInput",
    "InteractionContextInput",
    "VerifiedSelection",
    "VerifiedInteractionContext",
    "InteractionContextVerifier",
]
