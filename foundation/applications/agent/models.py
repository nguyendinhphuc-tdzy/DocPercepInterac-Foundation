"""Domain models for the Foundation Agent Architecture and Intent Layer.

Canonical identities are strictly (doc_id, element_id). `index` is only
display metadata and is never used to address or execute targets.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Authoritative reference to a specific document element."""
    doc_id: str
    element_id: str
    element_name: str
    type: str
    text_snippet: Optional[str] = None
    doc_name: Optional[str] = None


class AgentStep(BaseModel):
    """User-visible execution summary step (no hidden chain-of-thought)."""
    label: str
    status: Literal["done", "active", "pending"] = "done"


class ProposedAction(BaseModel):
    """Structured proposal for document mutation — requires explicit user confirmation."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["update_element", "batch_update"] = "update_element"
    doc_id: str
    doc_name: str
    element_id: str
    element_name: str
    current_value: str
    proposed_value: str
    rationale: str
    requires_confirmation: bool = True
    status: Literal["proposed", "executing", "applied", "rejected", "expired", "stale", "failed"] = "proposed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: int = 86400
    doc_hash: Optional[str] = None
    value_fingerprint: Optional[str] = None
    target_anchor: Optional[dict[str, Any]] = None


class AgentIntent(BaseModel):
    """Classified user intent."""
    intent_type: Literal["summarize", "inspect", "compare", "propose_edit", "query", "navigate"]
    target_doc_id: Optional[str] = None
    target_element_id: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class AgentContext(BaseModel):
    """Structured document context supplied to the Agent."""
    session_id: Optional[str] = None
    active_doc_id: Optional[str] = None
    selected_element: Optional[dict[str, Any]] = None
    available_documents: list[dict[str, Any]] = Field(default_factory=list)
    relevant_elements: list[dict[str, Any]] = Field(default_factory=list)


AgentModelId = Literal["luna", "sol"]

AGENT_MODELS: dict[AgentModelId, str] = {
    "luna": "gpt-5-6-luna-2026-07-09-gs-ae",
    "sol": "gpt-5-6-sol-2026-07-09-gs-ae",
}
DEFAULT_MODEL: AgentModelId = "luna"


def resolve_agent_model(model_key: Optional[str]) -> str:
    """Validates and resolves the model identifier ('luna' | 'sol') to its
    Workbench deployment name. Rejects any invalid or unsupported model."""
    if not model_key:
        return AGENT_MODELS[DEFAULT_MODEL]
    key = model_key.lower().strip()
    if key in AGENT_MODELS:
        return AGENT_MODELS[key]  # type: ignore[index]
    if key in AGENT_MODELS.values():
        return key
    raise ValueError(
        f"Unsupported model '{model_key}'. Supported models: {sorted(AGENT_MODELS.keys())}"
    )


def get_model_key(model_or_deployment: Optional[str]) -> AgentModelId:
    """Normalizes any model identifier or deployment string to 'luna' or 'sol'."""
    if not model_or_deployment:
        return DEFAULT_MODEL
    lower = model_or_deployment.lower().strip()
    if lower in AGENT_MODELS:
        return lower  # type: ignore[return-value]
    for k, v in AGENT_MODELS.items():
        if v.lower() == lower:
            return k
    return DEFAULT_MODEL


class AgentResponse(BaseModel):
    """Standardized Agent response payload."""
    response: str
    status: Literal["success", "error"] = "success"
    run_id: Optional[str] = None
    intent: Optional[str] = None
    model: AgentModelId = "luna"
    steps: list[AgentStep] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    error: Optional[str] = None
